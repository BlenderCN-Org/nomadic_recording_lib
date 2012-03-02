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

class EventDescriptor(object):
    _obj_property_attrs = ['name', 'wait_timeout']
    def __init__(self, **kwargs):
        self.name = kwargs.get('name')
        self.wait_timeout = kwargs.get('wait_timeout')
    def init_instance(self, obj):
        ekwargs = dict(zip(self._obj_property_attrs, [getattr(self, attr) for attr in self._obj_property_attrs]))
        ekwargs['parent_obj'] = obj
        e = Event(**ekwargs)
        obj.Events[e.name] = e
        return e
    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        e = obj.Events.get(self.name)
        if e is None:
            return
        return e._value
    def __set__(self, obj, value):
        e = obj.Events.get(self.name)
        if e is None:
            return
        e.state = value

class EventValue(int):
    @property
    def value(self):
        return self.event.state
    @value.setter
    def value(self, value):
        self.event.state = value
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
        return self.value
    

class Event(BaseObject, threading._Event):
    _Properties = {'state':dict(default=False), 
                   'wait_timeout':dict(type=float)}
    def __init__(self, **kwargs):
        threading._Event.__init__(self)
        BaseObject.__init__(self, **kwargs)
        self.name = kwargs.get('name')
        self.parent_obj = kwargs.get('parent_obj')
        self.type = bool
        self._value = EventValue(False)
        self._value.event = self
        self.wait_timeout = kwargs.get('wait_timeout')
        self._state_set_local = False
        self.bind(state=self._on_state_set)
    @property
    def value(self):
        return self.state
    @value.setter
    def value(self, value):
        self.state = value
    def bind(self, *args, **kwargs):
        if len(args) == 1:
            self.bind(state=args[0])
            return
        super(Event, self).bind(*args, **kwargs)
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
    def __nonzero__(self):
        return self.state

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
    _Properties = {'_thread_id':dict(default=''), 
                   'running':dict(default=False)}
    #               'running':dict(fset='_running_setter', fget='_running_setter'), 
    #               'stopped':dict(fset='_stopped_getter', fget='_stopped_setter')}
    def __new__(*args, **kwargs):
        cls = args[0]
        if cls != BaseThread:
            while issubclass(cls, BaseThread):
                events = getattr(cls, '_Events', {})
                for key, val in events.iteritems():
                    e_kwargs = val.copy()
                    e_kwargs.setdefault('name', key)
                    e = EventDescriptor(**e_kwargs)
                    setattr(cls, e.name, e)
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
                edesc = getattr(cls, key)
                if not isinstance(edesc, EventDescriptor):
                    continue
                e = edesc.init_instance(self)
                if e.wait_timeout is not None:
                    timed_events.append(e.name)
                self.Properties[e.name] = e
#            for key, val in cls._Events.iteritems():
#                ekwargs = val.copy()
#                ekwargs.setdefault('name', key)
#                ekwargs['parent_obj'] = self
#                e = Event(**ekwargs)
#                self.Events[e.name] = e
#                if e.wait_timeout is not None:
#                    timed_events.append(e.name)
#                setattr(self, e.name, e)
#                propname = e.name
#                if propname[0] == '_':
#                    propname = propname[1:]
#                if propname not in self.Properties:
#                    self.Properties[propname] = e
#                if not hasattr(self, propname):
#                    setattr(self, propname, e)
#                print self, e.name, propname
        timed_events.reverse()
        self.timed_events = timed_events
        self._threaded_calls_queue = collections.deque()
        self.disable_threaded_call_waits = kwargs.get('disable_threaded_call_waits', False)
        self.bind(running=self._on_running_set, 
                  _running=self._on__running_set)
    def _on_running_set(self, **kwargs):
        self._running = kwargs.get('value')
    def _on__running_set(self, **kwargs):
        self.running = kwargs.get('value')
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
        running = self.Events['_running']
        call_ready = self.Events['_threaded_call_ready']
        disable_call_waits = self.disable_threaded_call_waits
        do_calls = self._do_threaded_calls
        loop_iteration = self._thread_loop_iteration
        running.set()
        while running.is_set():
            if running.isSet():
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
            if self.running:
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
