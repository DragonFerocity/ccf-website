import urllib
from google.appengine.api import images
from google.appengine.ext import webapp, ndb
from . import Manage_BaseHandler
from scripts.database_models.staff_position import StaffPosition, StaffPosition_Form
from scripts.database_models.student_officer import StudentOfficer, StudentOfficer_Form
from scripts.database_models.board_member import BoardMember, BoardMember_Form


class Manage_StaffPositions_BaseHandler(Manage_BaseHandler):
    pass

########################
## STAFF
class Manage_StaffPositions_Handler(Manage_StaffPositions_BaseHandler):
    def get(self):
        self.generate_manage_bar()

        self.template_vars['existingStaffPositions'] = StaffPosition.gql("ORDER BY DisplayOrder ASC").fetch(50)
        self.template_vars['staff_form'] = self.generate_form(StaffPosition_Form)
        self.template_vars['staff_form'].Type.data = "Staff"

        self.template_vars['existingStudentOfficers'] = StudentOfficer.gql("ORDER BY DisplayOrder ASC").fetch(50)
        self.template_vars['officer_form'] = self.generate_form(StudentOfficer_Form)
        self.template_vars['officer_form'].Type.data = "Officer"

        self.template_vars['existingBoardMembers'] = BoardMember.gql("ORDER BY DisplayOrder ASC").fetch(50)
        self.template_vars['board_member_form'] = self.generate_form(BoardMember_Form)
        self.template_vars['board_member_form'].Type.data = "Board"

        self.render_template("manage/staff_positions/staff_positions.html")


    def post(self):
        def staff_post_process_model(filled_staff_position):
            filled_staff_position.Image = images.resize(filled_staff_position.Image, 108, 192)

            if not filled_staff_position.DisplayOrder:
                # TODO: only get DisplayOrder
                # displayOrderObject = GqlQuery("SELECT DisplayOrder FROM StudentOfficer ORDER BY DisplayOrder DESC").get()
                displayOrderObject = StaffPosition.gql("ORDER BY DisplayOrder DESC").get()
                if displayOrderObject and displayOrderObject.DisplayOrder:
                    filled_staff_position.DisplayOrder = displayOrderObject.DisplayOrder + 1
                else:
                    filled_staff_position.DisplayOrder = 1

        def officer_post_process_model(filled_student_officer):
            filled_student_officer.Image = images.resize(filled_student_officer.Image, 108, 192)

            if not filled_student_officer.DisplayOrder:
                # TODO: only get DisplayOrder
                # displayOrderObject = GqlQuery("SELECT DisplayOrder FROM StudentOfficer ORDER BY DisplayOrder DESC").get()
                displayOrderObject = StudentOfficer.gql("ORDER BY DisplayOrder DESC").get()
                if displayOrderObject and displayOrderObject.DisplayOrder:
                    filled_student_officer.DisplayOrder = displayOrderObject.DisplayOrder + 1
                else:
                    filled_student_officer.DisplayOrder = 1

        def board_member_post_process_model(filled_board_member):
            filled_board_member.Image = images.resize(filled_board_member.Image, 108, 192)

            if not filled_board_member.DisplayOrder:
                # TODO: only get DisplayOrder
                # displayOrderObject = GqlQuery("SELECT DisplayOrder FROM StudentOfficer ORDER BY DisplayOrder DESC").get()
                displayOrderObject = BoardMember.gql("ORDER BY DisplayOrder DESC").get()
                if displayOrderObject and displayOrderObject.DisplayOrder:
                    filled_board_member.DisplayOrder = displayOrderObject.DisplayOrder + 1
                else:
                    filled_board_member.DisplayOrder = 1

        if self.request.get("Type") == "Staff":
            filled_staff_position = self.process_form(StaffPosition_Form, StaffPosition, PostProcessing=staff_post_process_model)

            if filled_staff_position:
                self.redirect(self.request.path)
            else:
                self.redirect(self.request.path + '?edit=%s&retry=1' % self.request.get("edit"))
        elif self.request.get("Type") == "Officer":
            filled_student_officer = self.process_form(StudentOfficer_Form, StudentOfficer, PostProcessing=officer_post_process_model)
            if filled_student_officer:
                self.redirect(self.request.path)
            else:
                self.redirect(self.request.path + '?edit=%s&retry=1' % self.request.get("edit"))
        elif self.request.get("Type") == "Board":
            filled_board_member = self.process_form(BoardMember_Form, BoardMember, PostProcessing=board_member_post_process_model)
            if filled_board_member:
                self.redirect(self.request.path)
            else:
                self.redirect(self.request.path + '?edit=%s&retry=1' % self.request.get("edit"))


class Manage_StaffPositions_OrderHandler(Manage_StaffPositions_BaseHandler):
    def get(self, direction, displayOrderToMove):
        displayOrderToMove = int(displayOrderToMove)
        # I am assuming displayOrder has no duplicates
        FirstObject = StaffPosition.gql("WHERE DisplayOrder = :1", displayOrderToMove).get()
        if direction == 'u':
            SecondObject = StaffPosition.gql("WHERE DisplayOrder < :1 ORDER BY DisplayOrder DESC",
                                              displayOrderToMove).get()
        else:
            SecondObject = StaffPosition.gql("WHERE DisplayOrder > :1 ORDER BY DisplayOrder ASC",
                                              displayOrderToMove).get()
        FirstObject.DisplayOrder, SecondObject.DisplayOrder = SecondObject.DisplayOrder, FirstObject.DisplayOrder
        FirstObject.put()
        SecondObject.put()
        self.redirect('/manage/staff_positions')


class Manage_StaffPositions_DeleteHandler(Manage_StaffPositions_BaseHandler):
    def get(self, urlsafe_key):
        resource = str(urllib.unquote(urlsafe_key))
        key = ndb.Key(urlsafe=resource)
        if key.kind() == "StaffPosition":
            key.delete()
        else:
            self.abort(400, "Can only delete kind 'StaffPosition'")
        self.redirect('/manage/staff_positions')

########################
## OFFICERS
class Manage_StudentOfficers_Handler(Manage_BaseHandler):
    pass

class Manage_StudentOfficers_OrderHandler(Manage_StudentOfficers_Handler):
    def get(self, direction, displayOrderToMove):
        displayOrderToMove = int(displayOrderToMove)
        # I am assuming displayOrder has no duplicates
        FirstObject = StudentOfficer.gql("WHERE DisplayOrder = :1", displayOrderToMove).get()
        if direction == 'u':
            SecondObject = StudentOfficer.gql("WHERE DisplayOrder < :1 ORDER BY DisplayOrder DESC",
                                              displayOrderToMove).get()
        else:
            SecondObject = StudentOfficer.gql("WHERE DisplayOrder > :1 ORDER BY DisplayOrder ASC",
                                              displayOrderToMove).get()
        FirstObject.DisplayOrder, SecondObject.DisplayOrder = SecondObject.DisplayOrder, FirstObject.DisplayOrder
        FirstObject.put()
        SecondObject.put()
        self.redirect('/manage/staff_positions')


class Manage_StudentOfficers_DeleteHandler(Manage_StudentOfficers_Handler):
    def get(self, urlsafe_key):
        urlsafe_key = str(urllib.unquote(urlsafe_key))
        key = ndb.Key(urlsafe=urlsafe_key)
        if key.kind() == "StudentOfficer":
            key.delete()
        else:
            self.abort(400, "Can only delete kind 'StudentOfficer'")
        self.redirect('/manage/staff_positions')

########################
## BOARD MEMBERS
class Manage_BoardMember_Handler(Manage_BaseHandler):
    pass

class Manage_BoardMember_OrderHandler(Manage_BoardMember_Handler):
    def get(self, direction, displayOrderToMove):
        displayOrderToMove = int(displayOrderToMove)
        # I am assuming displayOrder has no duplicates
        FirstObject = BoardMember.gql("WHERE DisplayOrder = :1", displayOrderToMove).get()
        if direction == 'u':
            SecondObject = BoardMember.gql("WHERE DisplayOrder < :1 ORDER BY DisplayOrder DESC",
                                              displayOrderToMove).get()
        else:
            SecondObject = BoardMember.gql("WHERE DisplayOrder > :1 ORDER BY DisplayOrder ASC",
                                              displayOrderToMove).get()
        FirstObject.DisplayOrder, SecondObject.DisplayOrder = SecondObject.DisplayOrder, FirstObject.DisplayOrder
        FirstObject.put()
        SecondObject.put()
        self.redirect('/manage/staff_positions')


class Manage_BoardMember_DeleteHandler(Manage_BoardMember_Handler):
    def get(self, urlsafe_key):
        urlsafe_key = str(urllib.unquote(urlsafe_key))
        key = ndb.Key(urlsafe=urlsafe_key)
        if key.kind() == "BoardMember":
            key.delete()
        else:
            self.abort(400, "Can only delete kind 'BoardMember'")
        self.redirect('/manage/staff_positions')


application = webapp.WSGIApplication([
    ('/manage/staff_positions/staff/order/([ud])/(\d+)', Manage_StaffPositions_OrderHandler),
    ('/manage/staff_positions/staff/delete/([^/]+)', Manage_StaffPositions_DeleteHandler),
    ('/manage/staff_positions/officer/order/([^/]+)', Manage_StudentOfficers_OrderHandler),
    ('/manage/staff_positions/officer/delete/([^/]+)', Manage_StudentOfficers_DeleteHandler),
    ('/manage/staff_positions/board/order/([^/]+)', Manage_BoardMember_OrderHandler),
    ('/manage/staff_positions/board/delete/([^/]+)', Manage_BoardMember_DeleteHandler),
    ('/manage/staff_positions.*', Manage_StaffPositions_Handler),
    ], debug=Manage_BaseHandler.debug)
