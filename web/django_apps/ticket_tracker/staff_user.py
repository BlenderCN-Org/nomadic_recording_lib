from django.db import models
from django.contrib.auth.models import User, Group

class StaffGroup(models.Model):
    group = models.OneToOneField(Group)
    def __unicode__(self):
        return unicode(self.group)
    
class StaffUser(models.Model):
    user = models.OneToOneField(User)
    @property
    def groups(self):
        return self.user.groups
    def __unicode__(self):
        return unicode(self.user)
    
