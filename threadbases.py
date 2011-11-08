#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# threadbases.py
# Copyright (c) 2011 Matthew Reid

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
        
