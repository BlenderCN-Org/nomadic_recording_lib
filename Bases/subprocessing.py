import multiprocessing
import multiprocessing.managers
    
from osc_base import OSCBaseObject
import Properties
    
SUBPROCESSES = {}

def get_subprocesses():
    return SUBPROCESSES

def BuildSubProcess(cls, name, parent=None, **kwargs):
    assert name not in SUBPROCESSES, 'SubProcess %s already exists' % (name)
    sp = SubProcess(cls=cls, name=name, SubProcessParent=parent, kwargs=kwargs)
    SUBPROCESSES[sp.name] = sp
    sp.start()
    sp.obj_init.wait()
    obj = sp.out_queue.get()
    #print name, obj
    return obj
    
class SubProcess(multiprocessing.Process):
    def __init__(self, **kwargs):
        self.cls = kwargs.get('cls')
        self._obj = None
        pkwargs = {}
        for key in ['name', 'args', 'kwargs']:
            if key not in kwargs:
                continue
            pkwargs[key] = kwargs[key]
        super(SubProcess, self).__init__(**pkwargs)
        self.SubProcessParent = kwargs.get('SubProcessParent')
        self.running = multiprocessing.Event()
        self.obj_init = multiprocessing.Event()
        self.in_queue = multiprocessing.Queue()
        self.out_queue = multiprocessing.Queue()
    @property
    def obj(self):
        return self._obj
    def run(self):
        in_queue = self.in_queue
        running = self.running
        running.set()
        args = self._args
        kwargs = self._kwargs
        obj = self.cls(*args, **kwargs)
        obj.SubProcess = self
        self._obj = obj
        self.send_item(obj)
        self.obj_init.set()
        while running.is_set():
            item = in_queue.get()
            if isinstance(item, QueueTerminator):
                self.running.clear()
            else:
                self.process_item(item)
    def stop(self):
        self.in_queue.put(QueueTerminator())
    def send_item(self, item):
        self.out_queue.put(item)
    def process_item(self, item):
        pass
        
class QueueTerminator(object):
    pass
    
class Manager(multiprocessing.managers.SyncManager):
    def __init__(self, **kwargs):
        self.SubProcessParent = kwargs.get('SubProcessParent')
        self.SubProcessName = kwargs.get('SubProcessName')
        super(Manager, self).__init__(**kwargs)
        self.PropertyQueue = self.Queue()
        self.SignalQueue = self.Queue()
        self._Properties = {}
        self._Signals = set()
        for prop in self.SubProcessParent.Properties.itervalues():
            self.register_Property(prop)
        for sig in self.SubProcessParent._emitters.iterkeys():
            self.register_Signal(sig)
    def register_Property(self, prop):
        self._Properties[prop.name] = prop
    def register_Signal(self, sig):
        self._Signals.add(sig)
    def send_Property(self, **kwargs):
        prop = kwargs.get('Property')
        value = kwargs.get('value')
        if prop._type is not None:
            ptype = getattr(self, prop.type.__name__)
            value = ptype(value)
        d = self.dict()
        #d.update({'name':prop.name, 
        #self.PropertyQueue.put(
                
class PropertyProxy(multiprocessing.managers.BaseProxy):
    _exposed_ = ('_get_range', '_set_range', 
                 '_get_normalized', '_set_normalized', 
                 '_get_noramlized_and_offset', '_set_noramlized_and_offset', 
                 'set_value')
    def __init__(self, *args, **kwargs):
        super(PropertyProxy, self).__init__(*args)
        self._Property = kwargs.get('Property')
        

class PropertyConnectorProxy(multiprocessing.managers.BaseProxy, Properties.PropertyConnector):
    _exposed_ = ('set_Property_value', 'get_Property_value', 'on_Property_value_changed')
    def __init__(self, *args, **kwargs):
        super(PropertyProxy, self).__init__(*args)
        self.Property = kwargs.get('Property')
        
