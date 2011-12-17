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
import weakref

from BaseObject import BaseObject
from osc_base import OSCBaseObject
from misc import setID

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

_THREADS = weakref.WeakValueDictionary()

def add_call_to_thread(call, *args, **kwargs):
    obj = getattr(call, 'im_self', None)
    if not isinstance(obj, BaseThread):
        return False
    obj.insert_threaded_call(call, *args, **kwargs)
    return True

class BaseThread(OSCBaseObject, threading.Thread):
    def __init__(self, **kwargs):
        thread_id = setID(kwargs.get('thread_id'))
        if thread_id in _THREADS:
            raise
        self._thread_id = thread_id
        _THREADS[thread_id] = self
        threading.Thread.__init__(self, name=thread_id)
        OSCBaseObject.__init__(self, **kwargs)
        self._running = Event()
        self._stopped = Event()
        self._threaded_call_ready = Event()
        self._threaded_call_timeout = kwargs.get('threaded_call_timeout', .1)
        self._threaded_calls_queue = collections.deque()
    def insert_threaded_call(self, call, *args, **kwargs):
        args = tuple(args)
        kwargs = kwargs.copy()
        self._threaded_calls_queue.append((call, args, kwargs))
        self._threaded_call_ready.set()
    def run(self):
        running = self._running
        call_ready = self._threaded_call_ready
        call_timeout = self._threaded_call_timeout
        do_calls = self._do_threaded_calls
        loop_iteration = self._thread_loop_iteration
        running.set()
        while running.is_set():
            loop_iteration()
            call_ready.wait(call_timeout)
            do_calls()
        self._stopped.set()
    def stop(self):
        self._running.clear()
        self._threaded_calls_queue.clear()
        self._threaded_call_ready.set()
    def _thread_loop_iteration(self):
        pass
    def _do_threaded_calls(self):
        queue = self._threaded_calls_queue
        if not len(queue):
            self._threaded_call_ready.clear()
            return
        call, args, kwargs = queue.popleft()
        call(*args, **kwargs)
        
