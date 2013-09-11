from django.db import models
from django.utils import timezone

class Contact(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(max_length=254, unique=True)
    class Meta:
        unique_together = (('first_name', 'last_name'), )
    
class TicketStatus(models.Model):
    name = models.CharField(max_length=30)
    ticket_active = models.BooleanField()
    
class Ticket(models.Model):
    tracker = models.ForeignKey('ticket_tracker.Tracker')
    contact = models.ForeignKey(Contact)
    description = models.OneToOneField('ticket_tracker.InitialMessage', related_name='initial_message_parent_ticket')
    status = models.ForeignKey(TicketStatus, blank=True)
    active = models.BooleanField(default=True)
    created = models.DateTimeField(default=timezone.now())
    modified = models.DateTimeField(blank=True)
    class Meta:
        get_latest_by = 'created'
        ordering = ['created']
    def save(self, *args, **kwargs):
        def do_save():
            super(Ticket, self).save(*args, **kwargs)
        self.modified = timezone.now()
        do_save()
    
class MessageBase(models.Model):
    ticket = models.ForeignKey(Ticket)
    date = models.DateTimeField(default=timezone.now())
    subject = models.CharField(max_length=300, null=True, blank=True)
    text = models.TextField()
    hidden_data = models.TextField(blank=True, null=True)
    class Meta:
        abstract = True
        get_latest_by = 'date'
        ordering = ['date']
    
class InitialMessage(MessageBase):
    pass

class ContactMessage(MessageBase):
    @property
    def contact(self):
        return self.ticket.contact
    
class StaffMessageBase(MessageBase):
    user = models.ForeignKey('ticket_tracker.StaffUser')
    class Meta:
        abstract = True
    
class StaffMessage(StaffMessageBase):
    pass
    
class StaffOnlyNote(StaffMessageBase):
    pass
    
