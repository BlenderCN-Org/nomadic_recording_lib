import threading
import collections

from BaseObject import BaseObject

class Event(BaseObject, threading.Event):
    _Properties = {'state':dict(default=False)}
    def __init__(self, **kwargs):
        threading.Event.__init__(self)
        BaseObject.__init__(self, **kwargs)
        self._state_set_local = False
        self.bind(state=self._on_state_set)
    def set(self):
        threading.Event.set(self)
        self._state_set_local = True
        self.state = True
        self._state_set_local = False
    def clear(self):
        threading.Event.clear(self)
        self._state_set_local = True
        self.state = False
        self._state_set_local = False
    def _on_state_set(self, **kwargs):
        if self._state_set_local:
            return
        state = kwargs.get('value')
        if state:
            self.set()
        else:
            self.clear()
        
class ChannelEvent(BaseObject):
    _Properties = {'state':dict(default=False)}
    def __init__(self, **kwargs):
        super(ChannelEvent, self).__init__(**kwargs)
        self._on_event = Event()
        self._off_event = Event()
        self._off_event.state = True
        self._on_event.bind(state=self._on_event_state_set)
        self._off_event.bind(state=self._off_event_state_set)
    def _on_event_state_set(self, **kwargs):
        pass
    def _off_event_state_set(self, **kwargs):
        pass

class BaseThread(BaseObject, threading.Thread):
    def __init__(self, **kwargs):
        threading.Thread.__init__(self)
        BaseObject.__init__(self, **kwargs)
        
