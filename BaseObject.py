import UserDict
import atexit

import SignalDispatcher
from Serialization import Serializer
from Properties import ClsProperty

save_keys = {}
for key in ['saved_attributes', 'saved_child_classes', 'saved_child_objects']:
    save_keys.update({key:'_%s' % (key)})

class BaseObject(SignalDispatcher.dispatcher, Serializer):
    '''Base class for everything.  Too many things to document.
    
    '''
    #_saved_class_name = 'BaseObject'
    _saved_attributes = ['categories_id', 'Index']
    signals_to_register = ['property_changed']
    _Properties = {'Index':dict(type=int, fvalidate='_Index_validate')}
    def __new__(*args, **kwargs):
        cls = args[0]
        if cls != BaseObject:
            while issubclass(cls, BaseObject):
                props = getattr(cls, '_Properties', {})
                for key, val in props.iteritems():
                    if not hasattr(cls, key):
                        p_kwargs = val.copy()
                        p_kwargs.setdefault('name', key)
                        p_kwargs['cls'] = cls
                        property = ClsProperty(**p_kwargs)
                        setattr(cls, property.name, property)
                cls = cls.__bases__[0]
        return SignalDispatcher.dispatcher.__new__(*args, **kwargs)
        
    def __init__(self, **kwargs):
        self.Properties = {}
        self._Index_validate_default = True
        cls = self.__class__
        #bases_limit = getattr(cls, '_saved_bases_limit', self._saved_class_name)
        signals_to_register = set()
        save_dict = {}
        for key in save_keys.iterkeys():
            save_dict.update({key:set()})
        self.SettingsProperties = {}
        self.SettingsPropKeys = []
        self.ChildGroups = {}
        childgroups = {}
        while cls != BaseObject.__bases__[0]:# and getattr(cls, '_saved_class_name', '') != bases_limit:
            if not hasattr(self, 'saved_class_name'):
                if hasattr(cls, '_saved_class_name'):
                    self.saved_class_name = cls._saved_class_name
            signals = getattr(cls, 'signals_to_register', None)
            if signals is not None:
                for s in signals:
                    signals_to_register.add(s)
            for key, val in save_keys.iteritems():
                if hasattr(cls, val):
                    save_dict[key] |= set(getattr(cls, val))
            for propname in getattr(cls, '_Properties', {}).iterkeys():
                prop = getattr(cls, propname)
                if isinstance(prop, ClsProperty):
                    prop.init_instance(self)
            if hasattr(cls, '_SettingsProperties'):
                self.SettingsPropKeys.extend(cls._SettingsProperties)
                for propname in cls._SettingsProperties:
                    prop = self.Properties.get(propname)
                    if prop:
                        self.SettingsProperties.update({propname:prop})
                save_dict['saved_attributes'] |= set(cls._SettingsProperties)
            if hasattr(cls, '_ChildGroups'):
                childgroups.update(cls._ChildGroups)
            cls = cls.__bases__[0]
        self.SettingsPropKeys = tuple(self.SettingsPropKeys)
        for key, val in save_dict.iteritems():
            if not hasattr(self, key):
                setattr(self, key, val)
            
        if not hasattr(self, 'root_category'):
            self.root_category = kwargs.get('root_category')
        self.categories = {}
        self.categories_id = kwargs.get('categories_id', set())
        
        kwargs.update({'signals_to_register':signals_to_register})
        SignalDispatcher.dispatcher.__init__(self, **kwargs)
        
        prebind = kwargs.get('prebind', {})
        self.bind(**prebind)
        
        childgroup = kwargs.get('ChildGroup_parent')
        if childgroup is not None:
            self.ChildGroup_parent = childgroup
            
        for key, val in childgroups.iteritems():
            cgkwargs = val.copy()
            cgkwargs.setdefault('name', key)
            self.add_ChildGroup(**cgkwargs)
        
        Serializer.__init__(self, **kwargs)
        
        i = kwargs.get('Index')
        if self.Index is None and i is not None:
            self.Index = i
        
        self.register_signal('category_update')
        
        for c_id in self.categories_id:
            category = self.root_category.find_category(id=c_id)
            if category:
                self.add_category(category)
            else:
                bob
            
        f = getattr(self, 'on_program_exit', None)
        if f:
            atexit.register(f)
            
    def bind(self, **kwargs):
        '''Binds Properties and/or signals to the given callbacks.
        Bindings are made by keyword arguments.
        Example:
            SomeObject.bind(some_property_name=self.some_callback,
                            some_signal_name=self.some_other_callback)        
        '''
        for key, val in kwargs.iteritems():
            if key in self.Properties:
                self.Properties[key].bind(val)
            if key in self._emitters:
                self.connect(key, val)
        
    def unbind(self, *args):
        '''Unbinds (disconnects) the given callback(s) or object(s).  From any
        Property and/or signal that is bound.
        Multiple arguments are evaluated.  If an object is given, this will
        search for and unbind any callbacks that belong to that object.
        '''
        results = []
        for arg in args:
            result = False
            for prop in self.Properties.itervalues():
                r = prop.unbind(arg)
                if r:
                    result = True
            if not callable(arg):
                r = SignalDispatcher.dispatcher.disconnect(self, obj=arg)
                if r:
                    result = True
            elif len(self.find_signal_keys_from_callback(arg)['signals']):
                r = SignalDispatcher.dispatcher.disconnect(self, callback=arg)
                if r:
                    result = True
            results.append(result)
        if False in results:
            print 'could not unbind: ', self, zip(args, results)
        
    def disconnect(self, **kwargs):
        result = SignalDispatcher.dispatcher.disconnect(self, **kwargs)
        if not result:
            print 'could not disconnect: ', self, kwargs
        return result
    
    def add_category(self, category):
        id = category.id
        self.categories.update({id:category})
        self.categories_id.add(id)
        if self not in category.members:
            category.add_member(self)
        self.emit('category_update', obj=self, category=category, state=True)
            
    def remove_category(self, category):
        if hasattr(category, 'name'):
            id = category.id
        else:
            id = category
        if self in self.categories[id].members:
            self.categories[id].del_member(self)
        self.categories.pop(id, None)
        self.categories_id.discard(id)
        self.emit('category_update', obj=self, category=category, state=False)
        
    def unlink(self):
        for category in self.categories.copy().values():
            category.del_member(self)
            
    def _Index_validate(self, value):
        if not hasattr(self, 'ChildGroup_parent'):
            return self._Index_validate_default
        return self.ChildGroup_parent.check_valid_index(value)
        
    def add_child_object(self, kwargs):
        kwargs.setdefault('root_category', self.root_category)
        if self.osc_enabled:
            kwargs.setdefault('osc_parent_node', self.osc_node)
            
    def add_ChildGroup(self, **kwargs):
        if self.osc_enabled:
            kwargs.setdefault('osc_parent_node', self.osc_node)
        cg = ChildGroup(**kwargs)
        self.ChildGroups.update({cg.name:cg})
        setattr(self, cg.name, cg)
        return cg
        
    @property
    def GLOBAL_CONFIG(self):
        return globals()['GLOBAL_CONFIG']
    @GLOBAL_CONFIG.setter
    def GLOBAL_CONFIG(self, value):
        globals()['GLOBAL_CONFIG'].update(value)
        
from ChildGroup import ChildGroup

class _GlobalConfig(BaseObject, UserDict.UserDict):
    def __init__(self, **kwargs):
        BaseObject.__init__(self, **kwargs)
        self.register_signal('update')
        UserDict.UserDict.__init__(self)
    def __setitem__(self, key, item):
        old = self.data.copy()
        UserDict.UserDict.__setitem__(self, key, item)
        self.emit('update', key=key, item=item, old=old)
    def __delitem__(self, key):
        old = self.data.copy()
        UserDict.UserDict.__delitem__(self, key)
        self.emit('update', key=key, old=old)
    def update(self, d=None, **kwargs):
        old = self.data.copy()
        UserDict.UserDict.update(self, d, **kwargs)
        self.emit('update', old=old)
    def clear(self):
        old = self.data.copy()
        UserDict.UserDict.clear(self)
        self.emit('update', old=old)

GLOBAL_CONFIG = _GlobalConfig()
