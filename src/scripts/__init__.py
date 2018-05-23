import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ext'))

import cgi
import logging
import webapp2 as webapp
from google.appengine.api import memcache, users
from google.appengine.ext import ndb
from webapp2_extras import jinja2
from scripts.database_models.gae_setting import BaseSetting
from scripts.database_models.user_permission import UserPermission, Manage_Restricted_Pages, Other_Restricted_Pages
from ext.gaesessions import get_current_session
from datetime import datetime

class GAESettingDoesNotExist(Exception):
    pass


# http://stackoverflow.com/questions/3012421/python-lazy-property-decorator
def lazy_property(fn):
    attr_name = '_lazy_' + fn.__name__

    @property
    def _lazy_property(self):
        if not hasattr(self, attr_name):
            setattr(self, attr_name, fn(self))
        return getattr(self, attr_name)

    return _lazy_property

class global_settings(object):
    def __getattr__(self, name):
        db_value = BaseSetting.get_by_id(name)
        if db_value:
            return db_value.Value
        raise GAESettingDoesNotExist("'" + name + "' does not exist in the default values or in the datastore")


class BaseHandler(webapp.RequestHandler):
    debug = os.environ['SERVER_SOFTWARE'].startswith('Dev')

    def __init__(self, *args, **kwargs):
        super(BaseHandler, self).__init__(*args, **kwargs)
        self.settings = global_settings()
        self.template_vars = {}
        self.use_cache = True
        self.restricted = False
        now = datetime.utcnow()
        self.template_vars['seconds'] = 2

    def head(self):
        pass

    def generate_manage_bar(self):
        try:
            if users.is_current_user_admin():
                displayed_pages = Manage_Restricted_Pages.keys()
            else:
                user_permission = UserPermission.get_by_id(self.current_user.email().lower())
                displayed_pages = user_permission.PermittedPageClasses

            pages = {}
            for page in displayed_pages:
                if page in Other_Restricted_Pages:
                    continue

                group, link = Manage_Restricted_Pages[page]
                if group in pages:
                    pages[group].append(link)
                else:
                    pages[group] = [link, ]

            final_pages = []
            for group in sorted(pages.keys()):
                final_group = []
                for link in sorted(pages[group], key=lambda x: x[1]):
                    final_group.append(link)
                final_pages.append(final_group)

            self.template_vars['manage_pages'] = final_pages
        except:
            #self.template_vars['manage_pages'] = false
            pass

    # I should move to webapp2 sessions
    # http://webapp-improved.appspot.com/api/webapp2_extras/sessions.html
    @lazy_property
    def session(self):
        return get_current_session()

    @lazy_property
    def current_user(self):
        return users.get_current_user()

    @webapp.cached_property
    def jinja2(self):
        return jinja2.get_jinja2(app=self.app)

    def handle_exception(self, exception, debug_mode):
        # https://webapp-improved.appspot.com/guide/exceptions.html
        if debug_mode:
            raise

        # TODO: make a generic error page instead of 500 for everything
        if isinstance(exception, webapp.HTTPException):
            # just a simple http exception
            self.response.set_status(exception.code)
            if exception.code == 404:
                page_displayed_code = 404
            else:
                page_displayed_code = 500
        else:
            # some unknown bad exception
            logging.exception(exception)
            self.response.set_status(500)
            page_displayed_code = 500

        self.response.clear()
        template_file = "%s.html" % unicode(page_displayed_code)
        self.template_vars['title'] = "%s!" % unicode(page_displayed_code)
        self.template_vars['errorCode'] = page_displayed_code
        if exception.message:
            self.template_vars['errorMessage'] = "{}: {}".format(exception.__class__.__name__, exception.message)
        else:
            self.template_vars['errorMessage'] = exception.__class__.__name__
        self.template_vars['requestURL'] = self.request.url

        self.render_template(template_file)

    def _generate_memcache_key(self, url):
        return os.environ['CURRENT_VERSION_ID'] + url

    def clear_memcache(self, urls):
        memcache_keys = [self._generate_memcache_key(url) for url in urls]
        for memcache_key in memcache_keys:
            logging.info("Dropped memcache key: " + memcache_key)
        memcache.delete_multi(memcache_keys)

    def dispatch(self):
        if self.restricted and not users.is_current_user_admin():
            if self.current_user:
                user_permission = UserPermission.get_by_id(self.current_user.email().lower())
                if not user_permission:
                    self.abort(403)
                if not user_permission.check_permission(self.__class__):
                    self.abort(403)
            else:
                self.redirect(users.create_login_url(dest_url=self.request.url))

        if self.use_cache and self.request.method == "GET" and not self.debug:
            memcache_key = self._generate_memcache_key(self.request.path)
            response_values = memcache.get(memcache_key)

            if response_values:
                logging.info("Hit memcache key: " + memcache_key)
                self.response.headerlist = response_values[0]
                self.response.body = response_values[1]
            else:
                logging.info("Miss memcache key: " + memcache_key)
                super(BaseHandler, self).dispatch()
                # extract response body and headers and save them for the future
                response_values = (self.response.headerlist, self.response.body)
                memcache.add(memcache_key, response_values)
                logging.info("Added memcache key: " + memcache_key)
        else:
            logging.info("Skipping memcache: " + self.request.path)
            super(BaseHandler, self).dispatch()

    def render_template(self, filename):
        #self.generate_manage_bar()
        rendered_html = self.jinja2.render_template(filename, **self.template_vars)
        self.response.out.write(rendered_html)

    def generate_form(self, Form, Session_Key=None):
        if not Session_Key:
            Session_Key = self.request.path + Form.__class__.__name__

        edit_obj = None
        form_data = None
        if self.request.get('edit'):
            editKey = self.request.get("edit")
            self.template_vars['editKey'] = editKey
            edit_obj = ndb.Key(urlsafe=editKey).get()

        if self.request.get('retry'):
            form_data = self.session.get(Session_Key)

        form = Form(obj=edit_obj, formdata=form_data)
        if self.request.get('retry') and self.session.has_key(Session_Key):
            form.validate()

        return form

    def process_form(self, Form, DataStore_Model, Session_Key=None, PreProcessing=None, PostProcessing=None, raise_on_error=False):
        """
            expects edit key as "edit"
        """
        if not Session_Key:
            Session_Key = self.request.path + Form.__class__.__name__

        editKey = self.request.get("edit")
        if editKey:
            edit_obj = ndb.Key(urlsafe=editKey).get()
        else:
            edit_obj = None

        form = Form(self.request.POST, obj=edit_obj)

        if form.validate():
            form_data = form.data
            if editKey:
                filled_datastore_model = ndb.Key(urlsafe=editKey).get()
                if not filled_datastore_model:
                    self.abort(500, "The %s you are trying to edit does not exist" % DataStore_Model.__class__.__name__)
                # we can't set these on existing objects
                for kwarg in ('key', 'id', 'parent', 'namespace'):
                    if kwarg in form_data:
                        del form_data[kwarg]
            else:
                ctx_args = {}
                for kwarg in ('key', 'id', 'parent', 'namespace'):
                    if kwarg in form_data:
                        ctx_args[kwarg] = form_data[kwarg]
                        del form_data[kwarg]
                filled_datastore_model = DataStore_Model(**ctx_args)

            if PreProcessing:
                PreProcessing(form_data)
            filled_datastore_model.populate(**form_data)
            if PostProcessing:
                PostProcessing(filled_datastore_model)

            filled_datastore_model.put()
            if Session_Key in self.session:
                del self.session[Session_Key]
            return filled_datastore_model
        else:
            if raise_on_error:
                error_msg = form.errors
                self.abort(400, error_msg)
            else:
                # TODO: handle images better instead of just deleting the data
                # Save them to a temporary data model that gets cleaned out after a few days.
                post_data = self.request.POST
                for name in post_data:
                    if isinstance(post_data[name], cgi.FieldStorage):
                        del post_data[name]
                self.session[Session_Key] = post_data
                return None
