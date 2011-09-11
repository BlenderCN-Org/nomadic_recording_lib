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
        #super(SignalDispatcher, self).__init__(*args, **kwargs)
        self.__dict__.update({'_attrs_watched':{}})
        #self._signals = {}
        self._emitters = {}
        #self._receivers = {}
        self._signal_references = weakref.WeakValueDictionary()
        #self._attrs_watched = {}
        signals = list(kwargs.get('signals_to_register', []))
        self.register_signal(*signals)
        for key, val in kwargs.get('signals_to_connect', {}).iteritems():
            self.connect(key, val)
    def register_signal(self, *args):
        for signal in args:
            self._emitters.update({signal:SignalEmitter(name=signal)})
            #self._receivers.update({signal:{}})
    def register_attr_watch(self, *args):
        for attr_name in args:
            if attr_name[0] == '_':
                key = attr_name[1:]
            else:
                key = attr_name
            signal_name = 'attr_watch_' + key
            self._attrs_watched.update({attr_name:signal_name})
            self._emitters.update({signal_name:SignalEmitter(name=signal_name)})
            #self._receivers.update({signal_name:{}})
    def search_for_signal_name(self, search_string):
        results = []
        valid = False
        for signal in self._emitters.iterkeys():
            if search_string.lower() in signal.lower():
                results.append(signal)
                valid = True
        return results
#    def __setattr__(self, name, value):
#        #self.__dict__.update({name:value})
#        object.__setattr__(self, name, value)
#        if hasattr(self, '_attrs_watched'):
#            if name in self._attrs_watched.keys():
#                signal_name = self._attrs_watched[name]
#                attr_name = signal_name.split('attr_watch')[1]
#                self.emit(signal_name, object=self, name=attr_name, value=value)
    def emit(self, signal, **kwargs):
        new_kwargs = {}
        new_kwargs.update(kwargs)
        new_kwargs.update({'signal_name':signal})
        self._emitters[signal].emit(**new_kwargs)
        #print 'emiting: ', signal
    def connect(self, signal, callback):
        id = self._emitters[signal].add_receiver(callback=callback)
        #new_receiver = SignalReceiver(emitter=self._emitters[signal], callback=callback)
        #self._receivers[signal].update({new_receiver.id:new_receiver})
#        if hasattr(callback, 'im_self'):
#            obj = callback.im_self
#            if isinstance(obj, dispatcher):
#                obj._add_signal_reference(self, new_receiver.id)
            
        return id
        
    def disconnect(self, **kwargs):
        objID = kwargs.get('id')
        cb = kwargs.get('callback')
        obj = kwargs.get('obj')
        if obj is not None:
            keys = set()
            #print self, ' attempting obj disconnect: ', obj
            for e in self._emitters.itervalues():
                for rkey, r in e.receivers.iteritems():
                    if getattr(r, 'im_self', None) == obj:
                        keys.add(rkey)
            #print 'found keys: ', keys
            for key in keys:
                self.disconnect(id=key)
            return
            
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
                if objID in val.receivers:
                    signals.add(key)
        
        if len(signals):
            for key in signals:
                self._emitters[key].del_receiver(objID)
                #print '%s disconnected %s' % (self, found_key)
            return True
        
            
        #print 'could not disconnect: ', self, objID, cb
        return False
        
    def find_signal_keys_from_callback(self, cb):
        signals = set()
        objID = None
        for key, val in self._emitters.iteritems():
            for cbKey, cbVal in val.receivers.iteritems():
                if cb == cbVal:
                    signals.add(key)
                    objID = cbKey
        return dict(signals=signals, objID=objID)
    
    def old_disconnect(self, **kwargs):
        id = kwargs.get('id')
        callback = kwargs.get('callback')
        if id is not None:
            found_key = None
            for key, val in self._receivers.iteritems():
                if id in val.keys():
                    found_key = key
            if found_key is not None:
                del self._receivers[found_key][id]
                return True
        elif callback is not None:
            keys = None
            for sigKey, sigVal in self._receivers.iteritems():
                for recvKey, recvVal in sigVal.iteritems():
                    if recvVal.callback == callback:
                        keys = [sigKey, recvKey]
            if keys is not None:
                del self._receivers[keys[0]][keys[1]]
                return True
        print 'could not disconnect: ', self, id, callback
        return False
        
    def _add_signal_reference(self, obj, id):
        self._signal_references.update({id:obj})
        
#    def __del__(self):
#        print 'del'
#        for key, val in self._signal_references.iteritems():
#            print 'disconnecting'
#            val.disconnect(id=key)
    
    

class SignalEmitter(object):
    def __init__(self, **kwargs):
        self.name = kwargs.get('name')
        self.callbacks = set()
        self.receivers = {}#weakref.WeakValueDictionary()
        #self.recv_threads = {}
        
    def add_receiver(self, **kwargs):
        cb = kwargs.get('callback')
        objID = str(id(cb))
        #objID = setID(kwargs.get('id'))
        self.callbacks.add(cb)
        self.receivers.update({objID:cb})
        #self.recv_threads.update({objID:collections.deque()})
        return objID
        
    def del_receiver(self, objID):
        self.callbacks.discard(self.receivers.get(objID))
        if objID in self.receivers:
            del self.receivers[objID]
            
    def emit(self, *args, **kwargs):
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
    
class SignalReceiver(object):
    def __init__(self, **kwargs):
        self.emitter = kwargs.get('emitter')
        self.callback = kwargs.get('callback')
        self.id = setID(kwargs.get('id'))
        self.emitter.add_receiver(self)
    def __del__(self):
        self.emitter.del_receiver(self)
    def on_emission(self, *args, **kwargs):
        self.callback(*args, **kwargs)

#class oldSignalEmitter(gtkmvc.Model):
#    sgn = gtkmvc.observable.Signal()
#    __observables__ = ('sgn', )
#    def __init__(self):
#        gtkmvc.Model.__init__(self)
#        self.sgn = gtkmvc.observable.Signal()
#    def emit(self, **kwargs):
#        self.sgn.emit(kwargs)
#        #print 'emitter: ', kwargs
#
#
#class oldSignalReceiver(gtkmvc.Observer):
#    def __init__(self, **kwargs):
#        self.model = kwargs.get('emitter')
#        self.my_callback = kwargs.get('callback')
#        gtkmvc.Observer.__init__(self, self.model)
#        kwargs.setdefault('id', None)
#        self.id = setID(kwargs.get('id'))
#        #print 'receiver: ', self.model, self.my_callback
#    def property_sgn_signal_emit(self, *args, **kwargs):  
#        model = args[0]
#        new_kwargs = args[1]
#        if model == self.model:
#            #print "Signal:", model, args, kwargs  
#            #new_kwargs = kwargs.get('new_kwargs')
#            self.my_callback(**new_kwargs)
#        else:
#            print model, args, kwargs
#        return
    
#class Signals(object):
#    def __init__(self):
#        self.signals = {}
#        self.emitters = {}
#        self.receivers = {}
#    def register(self, signal_name, call):
#        self.emitters.update({signal_name:SignalEmitter()})
#        self.receivers.update({signal_name:set()})
#        return self.emitters[signal_name].emit
#    def connect(self, signal_name, callback):
#        if signal_name in self.receivers:
#            new_receiver = SignalReceiver(self.emitters[signal_name], callback)
#            receivers = self.receivers[signal_name]
#            receivers.add(new_receiver)
#            self.receivers.update({signal_name:receivers})
#    def emit(self, *args, **kwargs):
#        signal_name = args[0]
#        new_args = args[1:]
#        if signal_name in self.emitters:
#            self.emitters[signal_name].emit(new_args, kwargs)
