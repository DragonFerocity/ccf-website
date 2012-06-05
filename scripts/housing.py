from google.appengine.ext import webapp
from google.appengine.api.mail import EmailMessage
from scripts.main import BaseHandler
from scripts.gaesessions import get_current_session
from scripts.gaesettings import gaesettings
from scripts.database_models import HousingApplication
from wtforms.ext.appengine.db import model_form

class CchHandler(BaseHandler):
    def get(self):
        self.render_template("housing/cch.html",
        { 'title':"Christian Campus Fellowship Men's Housing Info",
          'HousingSelected':"top-level-dropdown-selected",
        })

class WcchHandler(BaseHandler):
    def get(self):
        self.render_template("housing/wcch.html",
        { 'title':"Christian Campus Fellowship Women's Housing Info",
          'HousingSelected':"top-level-dropdown-selected",
        })

class ApplicationHandler(BaseHandler):
    FormClass = model_form(HousingApplication)

    def get(self):
        session = get_current_session()
        if self.request.get('done'):
          self.render_template("housing/application_completion.html",
          { 'title':"Christian Campus Fellowship Housing Application",
            'HousingSelected':"top-level-dropdown-selected",
            'app_name':session.get("app-name"),
          })
        else:
          if self.request.get('retry'):
            form = self.FormClass(formdata=session.get('housing_application'))
            if session.has_key('housing_application'):
              form.validate()
          else:
            form = self.FormClass()
            house = self.request.get('house')
            if house == 'cch':
              form.House.data = "Men's Christian Campus House"
            elif house == 'wcch':
              form.House.data = "Women's Christian Campus House"

          self.render_template("housing/application.html",
          { 'title':"Christian Campus Fellowship Housing Application",
            'HousingSelected':"top-level-dropdown-selected",
            'form':form,
          })

    def post(self):
        session = get_current_session()
        form = self.FormClass(self.request.POST)
        if form.validate():
          if 'housing_application' in session:
            del session['housing_application']
          filled_housing_application = HousingApplication(**form.data)
          filled_housing_application.put()

          # send email
          message = EmailMessage()
          if form.House.data == "Men's Christian Campus House":
            message.sender = "CCH Housing Application <admin@rollaccf.org>"
            message.to = gaesettings.HousingApplicationCch_CompletionEmail
            message.subject = "CCH Housing Application (%s)" % form.FullName.data
          else:
            message.sender = "WCCH Housing Application <admin@rollaccf.org>"
            message.to = gaesettings.HousingApplicationWcch_CompletionEmail
            message.subject = "WCCH Housing Application (%s)" % form.FullName.data
          message.html = filled_housing_application.generateHtmlMailMessageBody();
          message.body = filled_housing_application.generatePlainTextMailMessageBody();
          message.send()

          session["app-name"] = filled_housing_application.FullName
          self.redirect(self.request.path + "?done=1")
        else:
          session['housing_application'] = self.request.POST
          self.redirect(self.request.path + '?retry=1')

class InfoHandler(BaseHandler):
    def get(self):
        self.render_template("housing/info.html",
        { 'title':"Christian Campus Fellowship Men's Housing Info",
          'headerText':"CCH Housing Information",
          'HousingSelected':"top-level-dropdown-selected",
        })

class CchFaqHandler(BaseHandler):
    def get(self):
        self.render_template("housing/cchfaq.html",
        { 'title':"Christian Campus House FAQ",
          'headerText':"Housing FAQ",
          'HousingSelected':"top-level-dropdown-selected",
        })

class WcchFaqHandler(BaseHandler):
    def get(self):
        self.render_template("housing/wcchfaq.html",
        { 'title':"Christian Campus House FAQ",
          'headerText':"Housing FAQ",
          'HousingSelected':"top-level-dropdown-selected",
        })

application = webapp.WSGIApplication([
  ('/housing/info.*', InfoHandler),
  ('/housing/cchfaq.*', CchFaqHandler),
  ('/housing/wcchfaq.*', WcchFaqHandler),
  ('/housing/cch.*', CchHandler),
  ('/housing/wcch.*', WcchHandler),
  ('/housing/application.*', ApplicationHandler),
  ], debug=True)
