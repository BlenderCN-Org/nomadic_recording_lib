#import gtkmvc
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
            self._emitters.update({signal:SignalEmitter(name=signal)})
            
#    def register_attr_watch(self, *args):
#        for attr_name in args:
#            if attr_name[0] == '_':
#                key = attr_name[1:]
#            else:
#                key = attr_name
#            signal_name = 'attr_watch_' + key
#            self._attrs_watched.update({attr_name:signal_name})
#            self._emitters.update({signal_name:SignalEmitter(name=signal_name)})
#            #self._receivers.update({signal_name:{}})

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
        new_kwargs = {}
        new_kwargs.update(kwargs)
        new_kwargs.update({'signal_name':signal})
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
        
    def old_disconnect(self, **kwargs):
        objID = kwargs.get('id')
        cb = kwargs.get('callback')
        obj = kwargs.get('obj')
        result = False
        if obj is not None:
            keys = set()
            #print self, ' attempting obj disconnect: ', obj
            for e in self._emitters.itervalues():
                for key in e.weakrefs:
                    if e.weakrefs[key] == obj:
                        keys.add(key[1])
                #for rkey, r in e.receivers.iteritems():
                #    if getattr(r, 'im_self', None) == obj:
                #        keys.add(rkey)
            #print 'found keys: ', keys
            for key in keys:
                r = self.disconnect(id=key)
                if r:
                    result = True
            return result
            
        #print kwargs
        #if objID is None:
        #    objID = id(cb)
        signals = set()
        if objID is None:
            d = self.find_signal_keys_from_callback(cb)
            signals |= d['signals']
            objID = d['objID']
        else:
            for key, val in self._emitters.iteritems():
                for rkey in val.weakrefs:
                    if objID in rkey:
                        signals.add(key)
                #if objID in val.receivers:
                #    signals.add(key)
        
        if len(signals):
            for key in signals:
                r = self._emitters[key].del_receiver(objID)
                if r:
                    result = True
            return result
        
            
        #print 'could not disconnect: ', self, objID, cb
        return False
        
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
                print 'REMOVE SIGNAL WEAKREF: ', self.name, wr.key
                del self.data[wr.key]
        self._remove = remove

class SignalEmitter(object):
    def __init__(self, **kwargs):
        self.name = kwargs.get('name')
        #self.callbacks = set()
        #self.receivers = {}#weakref.WeakValueDictionary()
        #self.recv_threads = {}
        self.weakrefs = MyWVDict(name=self.name)
        #self.weakrefs = weakref.WeakValueDictionary()
        
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
            
#    def del_receiver(self, objID):
#        found = None
#        for key in self.weakrefs:
#            if objID in key:
#                found = key
#                break
#        if found:
#            del self.weakrefs[found]
#            return True
#        return False
            
    def emit(self, *args, **kwargs):
        for key in self.weakrefs.keys()[:]:
            f, objID = key
            f(self.weakrefs[key], *args, **kwargs)
            
    def old_emit(self, *args, **kwargs):
        callbacks = set(self.callbacks)
        for cb in callbacks:
            cb(*args, **kwargs)
            
#        for key in self.receivers.keys():
#            t = ReceiverThread(target=self.receivers[key], id=key, exit_cb=self.on_thread_exit, args=args, kwargs=kwargs)
#            self.recv_threads[key].append(t)
#            if len(self.recv_threads[key]) == 1:
#                self.recv_threads[key].popleft().start()
                
            #cb = val()
            #print val
            #if cb is not None:
            #    cb(*args, **kwargs)
            #else:
            #    dead_ids.append(key)
        #for key in dead_ids:
        #    print 'removing ref: ', key
        #    del self.receivers[key]
        #    #recv.on_emission(*args, **kwargs)
#    def on_thread_exit(self, **kwargs):
#        key = kwargs.get('id')
#        if len(self.recv_threads[key]):
#            self.recv_threads[key].popleft().start()
            
#class ReceiverThread(threading.Thread):
#    def __init__(self, **kwargs):
#        threading.Thread.__init__(self)
#        self.target = kwargs.get('target')
#        self.id = kwargs.get('id')
#        self.exit_cb = kwargs.get('exit_cb')
#        self.args = kwargs.get('args', [])
#        self.kwargs = kwargs.get('kwargs', {})
#    def run(self):
#        self.target(*self.args, **self.kwargs)
#        self.exit_cb(id=self.id)
    
