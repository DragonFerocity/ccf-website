from os.path import join
from google.appengine.ext import webapp
from scripts.main import BaseHandler

class BeliefsHandler(BaseHandler):
    def get(self):
        self.render_template(join("aboutus", "beliefs.html"), { 'title':"CCF Beliefs", 'headerText':"CCF Beliefs" })

class ContactHandler(BaseHandler):
    def get(self):
        self.render_template(join("aboutus", "contact.html"), { 'title':"CCF Contact", 'headerText':"CCF Contact" })

class HistoryHandler(BaseHandler):
    def get(self):
        self.render_template(join("aboutus", "history.html"), { 'title':"CCF History", 'headerText':"CCF History" })

class LocationHandler(BaseHandler):
    def get(self):
        self.render_template(join("aboutus", "location.html"), { 'title':"CCF Location", 'headerText':"CCF Location" })

class StaffHandler(BaseHandler):
    def get(self):
        self.render_template(join("aboutus", "staff.html"), { 'title':"CCF Staff", 'headerText':"CCF Staff" })


application = webapp.WSGIApplication([
  ('/aboutus/beliefs.*', BeliefsHandler),
  ('/aboutus/contact.*', ContactHandler),
  ('/aboutus/history.*', HistoryHandler),
  ('/aboutus/location.*', LocationHandler),
  ('/aboutus/staff.*', StaffHandler),
  ], debug=True)
