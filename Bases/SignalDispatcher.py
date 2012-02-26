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
# SignalDispatcher.py
# Copyright (c) 2010 - 2011 Matthew Reid

import threading
import collections
import uuid
import weakref

RECEIVERS = 0

def setID(id):
    if id is None:
        id = str(uuid.uuid4()).replace('-', '_')
        #id = id.urn
    return 'UUID_' + id



class dispatcher(object):
    def __init__(self, *args, **kwargs):
        self.__dict__.update({'_attrs_watched':{}})
        self._emitters = {}
        self._signal_references = weakref.WeakValueDictionary()
        signals = list(kwargs.get('signals_to_register', []))
        self.register_signal(*signals)
        for key, val in kwargs.get('signals_to_connect', {}).iteritems():
            self.connect(key, val)
            
    def register_signal(self, *args):
        for signal in args:
            self._emitters.update({signal:SignalEmitter(name=signal, parent_obj=self)})
            
    def unlink(self):
        for e in self._emitters.itervalues():
            for wrkey in e.weakrefs.keys()[:]:
                e.del_receiver(wrkey=wrkey)
                
    def search_for_signal_name(self, search_string):
        results = []
        valid = False
        for signal in self._emitters.iterkeys():
            if search_string.lower() in signal.lower():
                results.append(signal)
                valid = True
        return results
        
    def emit(self, signal, **kwargs):
        new_kwargs = kwargs.copy()
        new_kwargs['signal_name'] = signal
        self._emitters[signal].emit(**new_kwargs)
        
    def connect(self, signal, callback):
        id = self._emitters[signal].add_receiver(callback=callback)            
        return id
        
    def disconnect(self, **kwargs):
        result = False
        for e in self._emitters.itervalues():
            r = e.del_receiver(**kwargs)
            if r:
                result = True
        return result
        
    def find_signal_keys_from_callback(self, cb):
        signals = set()
        objID = None
        for key, val in self._emitters.iteritems():
            for wrkey in val.weakrefs.keys()[:]:
                if cb.im_func == wrkey[0]:
                    signals.add(key)
                    objID = wrkey[1]
            #for cbKey, cbVal in val.receivers.iteritems():
            #    if cb == cbVal:
            #        signals.add(key)
            #        objID = cbKey
        return dict(signals=signals, objID=objID)
    
        
    def _add_signal_reference(self, obj, id):
        self._signal_references.update({id:obj})
        
    
class MyWVDict(weakref.WeakValueDictionary):
    def __init__(self, *args, **kwargs):
        self.name = kwargs.get('name')
        del kwargs['name']
        #super(MyWVDict, self).__init__(*args, **kwargs)
        weakref.WeakValueDictionary.__init__(self, *args, **kwargs)
        def remove(wr, selfref=weakref.ref(self)):
            self = selfref()
            if self is not None:
                #print 'REMOVE SIGNAL WEAKREF: ', self.name, wr.key
                del self.data[wr.key]
        self._remove = remove

class SignalEmitter(object):
    def __init__(self, **kwargs):
        self.name = kwargs.get('name')
        self.parent_obj = kwargs.get('parent_obj')
        self.weakrefs = weakref.WeakValueDictionary()
        
    @property
    def emission_thread(self):
        return getattr(self.parent_obj, 'ParentEmissionThread', None)
        
    def add_receiver(self, **kwargs):
        cb = kwargs.get('callback')
        #objID = str(id(cb))
        objID = id(cb.im_self)
        wrkey = (cb.im_func, objID)
        self.weakrefs[wrkey] = cb.im_self
        return objID
        
    def del_receiver(self, **kwargs):
        obj = kwargs.get('obj')
        cb = kwargs.get('callback')
        wrkey = kwargs.get('wrkey')
        if obj is not None:
            result = False
            found = set()
            for wrkey in self.weakrefs.keys():
                if wrkey[1] == id(obj):
                    found.add(wrkey)
            for wrkey in found:
                r = self.del_receiver(wrkey=wrkey)
                if r:
                    result = True
            return result
        if cb is not None:
            wrkey = (cb.im_func, id(cb.im_self))
            if wrkey in self.weakrefs:
                del self.weakrefs[wrkey]
                return True
        if wrkey is not None:
            if wrkey not in self.weakrefs:
                return False
            del self.weakrefs[wrkey]
            return True
            
    def emit(self, *args, **kwargs):
        t = self.emission_thread
        if t is not None and t._thread_id != threading.currentThread().name:
            #print 'Signal %s doing threaded emission to %s from %s' % (self.name, t._thread_id, threading.currentThread().name)
            t.insert_threaded_call(self._do_emit, *args, **kwargs)
        else:
            self._do_emit(*args, **kwargs)
            
    def _do_emit(self, *args, **kwargs):
        wrefs = self.weakrefs
        emission_thread = self.emission_thread
        for key in wrefs.keys()[:]:
            f, objID = key
            obj = wrefs[key]
            objthread = getattr(obj, 'ParentEmissionThread', None)
            if objthread is None or objthread == emission_thread:
                f(obj, **kwargs)
            else:
                m = getattr(obj, f.__name__)
                objthread.insert_threaded_call(m, **kwargs)
            
