import urllib
from google.appengine.ext import webapp, ndb
from scripts.database_models.user_permission import UserPermission, UserPermission_Form
from . import Manage_BaseHandler

class Manage_UserPermissions_BaseHandler(Manage_BaseHandler):
    pass

class Admin_UserPermissions_Handler(Manage_UserPermissions_BaseHandler):
    def get(self):
        self.generate_manage_bar()
        self.template_vars['user_permissions'] = UserPermission.query()
        self.template_vars['form'] = self.generate_form(UserPermission_Form)

        self.render_template("manage/user_permissions/user_permissions.html")

    def post(self):
        filled_user_permission = self.process_form(UserPermission_Form, UserPermission)
        if filled_user_permission:
            self.redirect(self.request.path)
        else:
            self.redirect(self.request.path + '?edit=%s&retry=1' % self.request.get("edit"))


class Admin_UserPermissions_DeleteHandler(Manage_UserPermissions_BaseHandler):
    def get(self, urlsafe_key):
        self.generate_manage_bar()
        urlsafe_key = str(urllib.unquote(urlsafe_key))
        key = ndb.Key(urlsafe=urlsafe_key)
        if key.kind() == 'UserPermission':
            key.delete()
        else:
            self.abort(400, "Can only delete kind 'UserPermission'")
        self.redirect('/manage/user_permissions')


application = webapp.WSGIApplication([
  ('/manage/user_permissions/delete/([^/]+)', Admin_UserPermissions_DeleteHandler),
  ('/manage/user_permissions.*', Admin_UserPermissions_Handler),
  ], debug=Manage_BaseHandler.debug)
