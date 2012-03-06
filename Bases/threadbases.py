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
from Properties import ObjProperty
from misc import setID, iterbases

class EventValue(int):
    @property
    def value(self):
        return bool(self.event.value)
    @value.setter
    def value(self, value):
        self.event.set_value(bool(value))
    @property
    def wait_timeout(self):
        return self.event.wait_timeout
    @wait_timeout.setter
    def wait_timeout(self, value):
        self.event.wait_timeout = value
    @property
    def state(self):
        return self.value
    @state.setter
    def state(self, value):
        self.value = value
    def isSet(self):
        return self.value
    def is_set(self):
        return self.value
    def set(self):
        self.event.set()
    def clear(self):
        self.event.clear()
    def wait(self, timeout=None):
        self.event.wait(timeout)
    def __nonzero__(self):
        return self > 0
    def __str__(self):
        return str(self > 0)

class Event(ObjProperty):
    __slots__ = ['wait_timeout', '_event', '_event_set_local']
    def __init__(self, **kwargs):
        self._event = threading.Event()
        self.wait_timeout = kwargs.get('wait_timeout', kwargs.get('max'))
        self._event_set_local = False
        value = kwargs.get('value', False)
        if not isinstance(value, EventValue):
            value = EventValue(value)
            value.event = self
        kwargs['value'] = value
        super(Event, self).__init__(**kwargs)
    def set_value(self, value):
        if not isinstance(value, EventValue):
            value = EventValue(value)
            value.event = self
        self._event_set_local = True
        if value:
            self.set()
        else:
            self.clear()
        self._event_set_local = False
        #print 'Event %s set_value: %s, current: %s' % (self.name, value, self.value)
        super(Event, self).set_value(value)
    def isSet(self):
        return bool(self.value)
    def is_set(self):
        return self.isSet()
    def set(self):
        self._event.set()
        if self._event_set_local:
            return
        self.set_value(True)
    def clear(self):
        self._event.clear()
        if self._event_set_local:
            return
        self.set_value(False)
    def wait(self, timeout=None):
        if timeout is None:
            timeout = self.wait_timeout
        self._event.wait(timeout)
    def __str__(self):
        return '<EventProperty %s of %s: value=%s, wait_timeout=%s>' % (self.name, self.parent_obj, self.isSet(), self.wait_timeout)
    
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
    _Properties = {'_thread_id':dict(default='')}
    def __new__(*args, **kwargs):
        cls = args[0]
        if cls != BaseThread:
            while issubclass(cls, BaseThread):
                events = getattr(cls, '_Events', None)
                if events is None:
                    continue
                props = getattr(cls, '_Properties', None)
                if props is None:
                    props = {}
                    setattr(cls, '_Properties', props)
                for key, val in events.iteritems():
                    e_kwargs = val.copy()
                    e_kwargs.setdefault('default', False)
                    if 'wait_timeout' in e_kwargs:
                        e_kwargs['max'] = e_kwargs['wait_timeout']
                    e_kwargs['ObjPropertyClass'] = Event
                    props[key] = e_kwargs
                cls = cls.__bases__[0]
        return OSCBaseObject.__new__(*args, **kwargs)
    def __init__(self, **kwargs):
        kwargs['ParentEmissionThread'] = None
        thread_id = setID(kwargs.get('thread_id'))
        if thread_id in _THREADS:
            self.LOG.warning('thread_id %s already exists' % (thread_id))
            thread_id = setID(None)
        
        _THREADS[thread_id] = self
        threading.Thread.__init__(self, name=thread_id)
        OSCBaseObject.__init__(self, **kwargs)
        self._thread_id = thread_id
        self.Events = {}
        timed_events = []
        
        for cls in iterbases(self, 'OSCBaseObject'):
            if not hasattr(cls, '_Events'):
                continue
            for key in cls._Events.iterkeys():
                e = self.Properties[key]
                self.Events[key] = e
                if e.wait_timeout is not None:
                    timed_events.append(e.name)
                    
        timed_events.reverse()
        self.timed_events = timed_events
        self._threaded_calls_queue = collections.deque()
        self.disable_threaded_call_waits = kwargs.get('disable_threaded_call_waits', False)
        
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
        disable_call_waits = self.disable_threaded_call_waits
        do_calls = self._do_threaded_calls
        loop_iteration = self._thread_loop_iteration
        self._running = True
        while self._running:
            if self._running:
                loop_iteration()
                if not disable_call_waits:
                    self._threaded_call_ready.wait()
                do_calls()
        self._stopped = True
        
    def stop(self, **kwargs):
        blocking = kwargs.get('blocking', False)
        wait_for_queues = kwargs.get('wait_for_queues', True)
        self._running = False
        if self._thread_id in _THREADS:
            del _THREADS[self._thread_id]
        if wait_for_queues:
            if not len(self._threaded_calls_queue):
                self._threaded_call_ready = True
            self._cancel_event_timeouts()
        else:
            self._threaded_calls_queue.clear()
            self._threaded_call_ready = True
        if not self.isAlive():
            self._stopped = True
        if blocking and threading.currentThread() != self:
            if type(blocking) in [float, int]:
                timeout = float(blocking)
            else:
                timeout = None
            self._stopped.wait(timeout)
        
    def _thread_loop_iteration(self):
        pass
        
    def _do_threaded_calls(self):
        queue = self._threaded_calls_queue
        if not len(queue):
            if self._running:
                self._threaded_call_ready = False
            return
        call, args, kwargs = queue.popleft()
        try:
            result = call(*args, **kwargs)
            return (result, call, args, kwargs)
        except:
            self.LOG.warning(traceback.format_exc())
        
if __name__ == '__main__':
    import sys, time
    def events_to_str(t):
        return ', '.join([str(e) for e in t.Events.values()])
    class TestThread(BaseThread):
        def __init__(self, **kwargs):
            self.last = time.time()
            super(TestThread, self).__init__(**kwargs)
        def test_call(self, **kwargs):
            now = time.time()
            print 'test_call %s: elapsed=%s, last=%s, now=%s' % (kwargs['i'], now - self.last, self.last, now)
            self.last = now
            #print 'thread_id=%s, current_thread=%s, kwargs=%s, events=%s\n' % (self._thread_id, threading.current_thread().name, kwargs, events_to_str(self))
        
    testthread = TestThread(thread_id='test')
    print 'before start: ', events_to_str(testthread)
    testthread.start()
    for i in range(5):
        #add_call_to_thread(testthread.test_call, i=i)
        testthread.insert_threaded_call(testthread.test_call, i=i)
    time.sleep(2.)
    testthread.stop(blocking=True)
    print 'after stop: ', events_to_str(testthread)
    sys.exit(0)
