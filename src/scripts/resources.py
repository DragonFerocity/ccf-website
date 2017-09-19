from google.appengine.ext import webapp
from scripts import BaseHandler
from scripts.database_models.partnership import Partnership


class Resources_BaseHandler(BaseHandler):
    def __init__(self, *args, **kwargs):
        super(Resources_BaseHandler, self).__init__(*args, **kwargs)
        self.template_vars['LinksSelected'] = "top-level-dropdown-selected"


class ResourcesHandler(Resources_BaseHandler):
    def get(self):
        self.render_template("resources/resources.html")

class PartnersHandler(Resources_BaseHandler):
    def get(self):
        self.template_vars['existingPartnerships'] = Partnership.gql("ORDER BY DisplayOrder ASC").fetch(50)
        self.render_template("resources/partners.html")


application = webapp.WSGIApplication([
    ('/resources/freshman.*', ResourcesHandler),
    ('/resources/partners.*', PartnersHandler),
    ], debug=BaseHandler.debug)
