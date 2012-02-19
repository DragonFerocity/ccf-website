from google.appengine.ext import db
from scripts.gaesettings import gaesettings

class HomepageSlide(db.Model):
  Enabled = db.BooleanProperty()
  DisplayOrder = db.IntegerProperty()

  Createdby = db.UserProperty(auto_current_user_add=True)
  CreationDateTime = db.DateTimeProperty(auto_now_add=True)
  Modifiedby = db.UserProperty(auto_current_user=True)
  ModifiedDateTime = db.DateTimeProperty(auto_now=True)

  Image = db.BlobProperty()
  Link = db.StringProperty()
  Title = db.StringProperty()
  Html = db.TextProperty()

  @db.ComputedProperty
  def CompleteURL(self):
    return '/'.join(('', gaesettings.HomepageLinkPrefix, self.Link))
