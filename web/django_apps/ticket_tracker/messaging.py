from email import message_from_string
import imaplib

from django.core.mail import get_connection, EmailMessage
from django.db import models

from models_default_builder.models import build_defaults

import email_template_defaults


class MailUserConf(models.Model):
    username = models.CharField(max_length=200)
    password = models.CharField(max_length=200)
    def __unicode__(self):
        return self.username
    
class MailConfigBase(models.Model):
    login = models.ForeignKey(MailUserConf, blank=True, null=True)
    hostname = models.CharField(max_length=200, blank=True, null=True)
    port = models.IntegerField(blank=True, null=True)
    use_ssl = models.BooleanField(default=False)
    class Meta:
        abstract = True
        
class IncomingMailConfig(MailConfigBase):
    protocol = models.CharField(max_length=10, 
                                choices=(('pop3', 'POP 3'), 
                                         ('imap', 'IMAP')), 
                                default='imap')
    check_interval = models.IntegerField(default=5, 
                                         help_text='Interval in minutes to check for new messages')
    last_check = models.DateTimeField(blank=True, null=True, editable=False)
    
class OutgoingMailConfig(MailConfigBase):
    pass
    
class EmailHandler(models.Model):
    email_address = models.EmailField(help_text='All outgoing emails will use this address')
    incoming_mail_configuration = models.ForeignKey(IncomingMailConfig, blank=True, null=True)
    outgoing_mail_configuration = models.ForeignKey(OutgoingMailConfig, blank=True, null=True)
    auto_response_template = models.ForeignKey('ticket_tracker.EmailMessageTemplate', blank=True, null=True)
    staff_response_template = models.ForeignKey('ticket_tracker.EmailMessageTemplate', blank=True, null=True)
    contact_response_template = models.ForeignKey('ticket_tracker.EmailMessageTemplate', blank=True, null=True)
    
class EmailMessageTemplate(models.Model):
    name = models.CharField(max_length=100, unique=True, 
                            help_text='Template name (not used as part of the generated message)')
    subject = models.CharField(max_length=300, blank=True, null=True, 
                               help_text='Message subject contents (can contain template tags)')
    body = models.TextField(blank=True, null=True, 
                            help_text='Message body contents (can contain template tags)')

build_defaults({'model':EmailMessageTemplate, 
                'unique':'name', 
                'defaults':email_template_defaults.defaults})
