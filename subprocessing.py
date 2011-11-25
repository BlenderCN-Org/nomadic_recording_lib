import multiprocessing
import multiprocessing.managers
    
from osc_base import OSCBaseObject
import Properties
    
class SubProcessBase(OSCBaseObject):
    def __init__(self, **kwargs):
        super(SubProcessBase, self).__init__(**kwargs)
        mkwargs = kwargs.copy()
        mkwargs.setdefault('SubProcessParent', self)
        mkwargs.setdefault('SubProcessName', getattr(self, 'SubProcessName', self.__class__.__name__))
        self._subprocess_manager = Manager(**mkwargs)
        self._subprocess_manager.start()
        
        
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
        
