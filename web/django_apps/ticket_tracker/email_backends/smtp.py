import traceback
from django.core.mail import get_connection, send_mail
from django.core.mail import EmailMessage as DjangoEmailMessage
from .base import BaseEmailBackend

django_backend = 'django.core.mail.backends.smtp.EmailBackend'

class SmtpBackend(BaseEmailBackend):
    def __init__(self, **kwargs):
        super(SmtpBackend, self).__init__(**kwargs)
        c = get_connection(django_backend, 
                           host=self.hostname, 
                           port=self.port, 
                           username=self.username, 
                           password=self.password, 
                           use_tls=self.use_ssl)
        self.smtp_connection = c
    def send_message(self, **kwargs):
        c = self.smtp_connection
        sender = kwargs.get('sender')
        recipients = kwargs.get('recipients')
        subject = kwargs.get('subject')
        body = kwargs.get('body')
        if not sender:
            sender = self.email_address
        if isinstance(recipients, basestring):
            recipients = [recipients]
        msg = DjangoEmailMessage(subject=subject, 
                                 body=body, 
                                 from_email=sender, 
                                 to=recipients, 
                                 connection=c)
        message = self._build_message(_message=msg)
        c.open()
        try:
            msg.send()
        except:
            traceback.print_exc()
        finally:
            c.close()
        return message
