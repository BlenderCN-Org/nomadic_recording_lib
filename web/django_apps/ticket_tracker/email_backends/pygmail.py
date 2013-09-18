import gmail
from .base import BaseEmailBackend

class PyGMailBackend(BaseEmailBackend):
    def _do_login(self):
        c = self.connection
        if c is None:
            c = gmail.login(self.username, self.password)
            self.connection = c
        return True
    def _do_logout(self):
        c = self.connection
        if c is None:
            return True
        c.logout()
    def _check_logged_in(self):
        c = self.connection
        if c is None:
            return False
        return c.logged_in
    def get_new_messages(self, **kwargs):
        mark_as_read = kwargs.get('mark_as_read')
        if not self.logged_in:
            self.login()
        c = self.connection
        msgs = c.inbox().mail(unread=True)
        for msg in msgs:
            msg.fetch()
            msgkwargs = {}
            for attr in ['message_id', 'thread_id', 'subject', 'body']:
                msgkwargs[attr] = getattr(msg, attr)
            msgkwargs['sender'] = msg.fr
            msgkwargs['recipients'] = msg.to.split(', ')
            msgkwargs['datetime'] = msg.sent_at
            message = self._build_message(**msgkwargs)
            if mark_as_read:
                msg.read()
            yield message
