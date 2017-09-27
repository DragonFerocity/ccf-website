from google.appengine.ext import ndb

from . import NdbBaseModel, NdbUtcDateTimeProperty, GaeFileField
from ext.wtforms import validators, fields
from ext.wtforms.form import Form


class BoardMember_Form(Form):
    Name = fields.TextField(u'Name ', validators=[validators.Required()])
    JoinDate = fields.IntegerField(u'Year started being a board member ', validators=[validators.Required()])
    Image = GaeFileField(u'Image ', validators=[validators.data_required()])
    Type = fields.HiddenField(u'Type');


class BoardMember(NdbBaseModel):
    relevant_page_urls = ["/aboutus/staff"]

    CreatedBy = ndb.UserProperty(auto_current_user_add=True)
    CreationDateTime = NdbUtcDateTimeProperty(auto_now_add=True)
    ModifiedBy = ndb.UserProperty(auto_current_user=True)
    ModifiedDateTime = NdbUtcDateTimeProperty(auto_now=True)
    DisplayOrder = ndb.IntegerProperty()

    Name = ndb.StringProperty(
        required=True,
    )
    Image = ndb.BlobProperty(
        required=True,
    )
    JoinDate = ndb.IntegerProperty(
        required=True,
    )
    Type = ndb.TextProperty(
    )
