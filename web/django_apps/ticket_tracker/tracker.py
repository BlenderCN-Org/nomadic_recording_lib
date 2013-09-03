from django.db import models

class Tracker(models.Model):
    name = models.CharField(max_length=100)
    staff_users = models.ManyToManyField('ticket_tracker.StaffUser', blank=True, null=True)
