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
import traceback
import collections
import weakref

from BaseObject import BaseObject
from osc_base import OSCBaseObject
from misc import setID, iterbases

class Event(BaseObject, threading._Event):
    _Properties = {'state':dict(default=False), 
                   'wait_timeout':dict(type=float)}
    def __init__(self, **kwargs):
        threading._Event.__init__(self)
        BaseObject.__init__(self, **kwargs)
        self.name = kwargs.get('name')
        self.wait_timeout = kwargs.get('wait_timeout')
        self._state_set_local = False
        self.bind(state=self._on_state_set)
    def set(self):
        threading._Event.set(self)
        self._state_set_local = True
        self.state = True
        self._state_set_local = False
    def clear(self):
        threading._Event.clear(self)
        self._state_set_local = True
        self.state = False
        self._state_set_local = False
    def wait(self, timeout=None):
        if timeout is None:
            timeout = self.wait_timeout
        threading._Event.wait(self, timeout)
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
    _Events = {'_running':{}, 
               '_stopped':{}, 
               '_threaded_call_ready':dict(wait_timeout=.1)}
    def __init__(self, **kwargs):
        kwargs['ParentEmissionThread'] = None
        thread_id = setID(kwargs.get('thread_id'))
        if thread_id in _THREADS:
            self.LOG.warning('thread_id %s already exists' % (thread_id))
            thread_id = setID(None)
        self._thread_id = thread_id
        _THREADS[thread_id] = self
        threading.Thread.__init__(self, name=thread_id)
        OSCBaseObject.__init__(self, **kwargs)
        self.Events = {}
        timed_events = []
        for cls in iterbases(self, 'OSCBaseObject'):
            if not hasattr(cls, '_Events'):
                continue
            for key, val in cls._Events.iteritems():
                ekwargs = val.copy()
                ekwargs.setdefault('name', key)
                e = Event(**ekwargs)
                self.Events[e.name] = e
                if e.wait_timeout is not None:
                    timed_events.append(e.name)
                setattr(self, e.name, e)
        timed_events.reverse()
        self.timed_events = timed_events
        self._threaded_calls_queue = collections.deque()
        self.disable_threaded_call_waits = kwargs.get('disable_threaded_call_waits', False)
    @property
    def running(self):
        return self._running.isSet()
    def insert_threaded_call(self, call, *args, **kwargs):
        args = tuple(args)
        kwargs = kwargs.copy()
        self._threaded_calls_queue.append((call, args, kwargs))
        self._cancel_event_timeouts()
    def _cancel_event_timeouts(self, events=None):
        if events is None:
            events = self.timed_events
        for key in events:
            e = self.Events.get(key)
            if not e:
                continue
            e.set()        
    def run(self):
        running = self._running
        call_ready = self._threaded_call_ready
        disable_call_waits = self.disable_threaded_call_waits
        do_calls = self._do_threaded_calls
        loop_iteration = self._thread_loop_iteration
        running.set()
        while running.is_set():
            loop_iteration()
            if not disable_call_waits:
                call_ready.wait()
            do_calls()
        self._stopped.set()
    def stop(self, **kwargs):
        blocking = kwargs.get('blocking', False)
        wait_for_queues = kwargs.get('wait_for_queues', True)
        self._running.clear()
        if self._thread_id in _THREADS:
            del _THREADS[self._thread_id]
        if wait_for_queues:
            if not len(self._threaded_calls_queue):
                self._threaded_call_ready.set()
            self._cancel_event_timeouts()
        else:
            self._threaded_calls_queue.clear()
            self._threaded_call_ready.set()
        if not self.isAlive():
            self._stopped.set()
        if blocking:
            self._stopped.wait()
        
    def _thread_loop_iteration(self):
        pass
    def _do_threaded_calls(self):
        queue = self._threaded_calls_queue
        if not len(queue):
            self._threaded_call_ready.clear()
            return
        call, args, kwargs = queue.popleft()
        try:
            result = call(*args, **kwargs)
            return (result, call, args, kwargs)
        except:
            self.LOG.warning(traceback.format_exc())
        
if __name__ == '__main__':
    class TestThread(BaseThread):
        def test_call(self, **kwargs):
            pass
            #print 'thread_id=%s, current_thread=%s, kwargs=%s' % (self._thread_id, threading.current_thread().name, kwargs)
    testthread = TestThread(thread_id='test')
    testthread.start()
    for i in range(5):
        add_call_to_thread(testthread.test_call, i=i)
    testthread.stop()
