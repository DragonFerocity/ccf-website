from google.appengine.ext import ndb

from . import NdbBaseModel, NdbUtcDateTimeProperty, GaeFileField
from ext.wtforms import validators, fields
from ext.wtforms.form import Form


class Partnership_Form(Form):
    Name = fields.TextField(u'Organization Name ', validators=[validators.Required()])
    WebsiteURL = fields.TextField(u'Website URL ', validators=[])
    Description = fields.TextAreaField(u'Description', validators=[validators.Required()])
    Image = GaeFileField(u'Image ', validators=[validators.data_required()])


class Partnership(NdbBaseModel):
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
    WebsiteURL = ndb.StringProperty(
    )
    Description = ndb.TextProperty(
        required=True,
    )
