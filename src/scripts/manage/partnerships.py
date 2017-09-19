import urllib
from google.appengine.api import images
from google.appengine.ext import webapp, ndb
from . import Manage_BaseHandler
from scripts.database_models.partnership import Partnership, Partnership_Form


class Manage_Partnerships_BaseHandler(Manage_BaseHandler):
    pass


class Manage_Partnerships_Handler(Manage_Partnerships_BaseHandler):
    def get(self):
        self.generate_manage_bar()
        self.template_vars['existingPartnerships'] = Partnership.gql("ORDER BY DisplayOrder ASC").fetch(50)
        self.template_vars['form'] = self.generate_form(Partnership_Form)

        self.render_template("manage/partnerships/partnerships.html")


    def post(self):
        def post_process_model(filled_partnership):
            #filled_partnership.Image = images.resize(filled_partnership.Image)

            if not filled_partnership.DisplayOrder:
                # TODO: only get DisplayOrder
                # displayOrderObject = GqlQuery("SELECT DisplayOrder FROM StudentOfficer ORDER BY DisplayOrder DESC").get()
                displayOrderObject = Partnership.gql("ORDER BY DisplayOrder DESC").get()
                if displayOrderObject and displayOrderObject.DisplayOrder:
                    filled_partnership.DisplayOrder = displayOrderObject.DisplayOrder + 1
                else:
                    filled_partnership.DisplayOrder = 1

        filled_partnership = self.process_form(Partnership_Form, Partnership, PostProcessing=post_process_model)

        if filled_partnership:
            self.redirect(self.request.path)
        else:
            self.redirect(self.request.path + '?edit=%s&retry=1' % self.request.get("edit"))


class Manage_Partnerships_OrderHandler(Manage_Partnerships_BaseHandler):
    def get(self, direction, displayOrderToMove):
        displayOrderToMove = int(displayOrderToMove)
        # I am assuming displayOrder has no duplicates
        FirstObject = Partnership.gql("WHERE DisplayOrder = :1", displayOrderToMove).get()
        if direction == 'u':
            SecondObject = Partnership.gql("WHERE DisplayOrder < :1 ORDER BY DisplayOrder DESC",
                                              displayOrderToMove).get()
        else:
            SecondObject = Partnership.gql("WHERE DisplayOrder > :1 ORDER BY DisplayOrder ASC",
                                              displayOrderToMove).get()
        FirstObject.DisplayOrder, SecondObject.DisplayOrder = SecondObject.DisplayOrder, FirstObject.DisplayOrder
        FirstObject.put()
        SecondObject.put()
        self.redirect('/manage/partnerships')


class Manage_Partnerships_DeleteHandler(Manage_Partnerships_BaseHandler):
    def get(self, urlsafe_key):
        resource = str(urllib.unquote(urlsafe_key))
        key = ndb.Key(urlsafe=resource)
        if key.kind() == "Partnership":
            key.delete()
        else:
            self.abort(400, "Can only delete kind 'Partnership'")
        self.redirect('/manage/partnerships')


application = webapp.WSGIApplication([
    ('/manage/partnerships/order/([ud])/(\d+)', Manage_Partnerships_OrderHandler),
    ('/manage/partnerships/delete/([^/]+)', Manage_Partnerships_DeleteHandler),
    ('/manage/partnerships.*', Manage_Partnerships_Handler),
    ], debug=Manage_BaseHandler.debug)
