from django.db import models
from django.contrib.auth.models import User, Group

class StaffGroup(models.Model):
    group = models.OneToOneField(Group)
    
class StaffUser(models.Model):
    user = models.OneToOneField(User)
    trackers_
