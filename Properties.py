import threading
import weakref

### testing commits on svn externals

def getbases(startcls, endcls=None, reverse=False):
    if endcls is None:
        endcls = 'object'
    clslist = []
    cls = startcls
    while cls.__name__ != endcls:
        clslist.append(cls)
        cls = cls.__bases__[0]
    clslist.append(cls)
    if reverse:
        clslist.reverse()
    #print clslist
    return clslist

class ClsProperty(object):
    '''Property that can be attached to a class.  Can be created automatically
    by adding a dictionary "_Properties" to an instance of BaseObject
    containing {'property_name':{option:value, ...}, ...}
    :Parameters:
        'name' : str, name of the Property
        'default_value' : if not None, this will be the default value when instances
            are initialized, otherwise None will be used.  default is None
        'type' : type, if not None, this will be used for type verification.
            Otherwise, the type will be assumed by either the 'default_value'
            or the first value given to the Property.  default is None
        'ignore_type' : bool, whether type verification will be used.  default is True
        'min' : if not None, this will be used set the minimum allowed value.
            This attribute can also be modified on an instance of the Property.
            Currently, this has only been tested with int and float types. default is None
        'max' : if not None, this will be used set the maximum allowed value.
            This attribute can also be modified on an instance of the Property.
            Currently, this has only been tested with int and float types. default is None
        'ignore_range' : bool, whether to use the 'min' and 'max' attributes to
            verify value range, regardless of whether they are set as None. default is False
        'symbol' : str, string that can be used to format the value for output.
            default is an empty string
        'quiet' : bool, if True, BaseObject will emit the 'property_changed' signal
            any time this Property's value is changed.  If the Property is intended
            to be set rapidly (i.e. a fader value) set this to False to keep things
            running more efficiently.  default is False
        'fvalidate' : str, if not None, name of an instance method to validate
            a value (given as an argument).  The method must return True or False.
            This does not override the build-in type validation function.
            This must be a string that can be used with "getattr(self, 'method_name')".
            default is None
        'fformat' : str, if not None, name of an instance method to return a 
            formatted value (given as an argument) before being passed to the 
            setter method.
            This must be a string that can be used with "getattr(self, 'method_name')".
            default is None
        'fget' : str, if not None, name of an instance method to use to get the 
            value of the Property.  This will bypass the built-in getter.
            This must be a string that can be used with "getattr(self, 'method_name')".
            default is None
        'fset' : str, if not None, name of an instance method to use to set the 
            value of the Property.  This will bypass the built-in setter thus
            bypassing the built-in validation and formatting functionality.
            This must be a string that can be used with "getattr(self, 'method_name')".
            default is None
    '''
    
    _obj_property_attrs = ['name', 'min', 'max', 'symbol', 'type', 'quiet', 'ignore_range', 'threaded']
    def __init__(self, **kwargs):
        self.cls = kwargs.get('cls')
        self.name = kwargs.get('name')
        self.ignore_type = kwargs.get('ignore_type', False)
        self.ignore_range = kwargs.get('ignore_range', False)
        self.default_value = kwargs.get('default')
        self.min = kwargs.get('min')
        self.max = kwargs.get('max')
        self.symbol = kwargs.get('symbol', '')
        self.type = kwargs.get('type', type(self.default_value))
        self.quiet = kwargs.get('quiet', False)
        
        ## TODO: threading disabled for now. messes with gtk stuff (as i imagined)
        #self.threaded = kwargs.get('threaded', False)
        self.threaded = False
        
        for key in ['fget', 'fset', 'fvalidate', 'fformat']:
            fn = getattr(self, '_%s' % (key))
            attr = kwargs.get(key)
            clsfn = None
            if attr is not None:
                for cls in getbases(self.cls, 'BaseObject'):
                    clsfn = getattr(cls, attr, None)
                    if clsfn is not None:
                        #print 'clsfn: ', attr, clsfn
                        break
            if clsfn is not None:
                fn = clsfn
            setattr(self, key, fn)
        
    def init_instance(self, obj):
        pkwargs = dict(zip(self._obj_property_attrs, [getattr(self, attr) for attr in self._obj_property_attrs]))
        pkwargs.update({'obj':obj, 'value':self.default_value})
        obj.Properties[self.name] = ObjProperty(**pkwargs)
        
    def _fget(self, obj):
        return obj.Properties[self.name].value
        
    def _fset(self, obj, value):
        value = self.fformat(obj, value)
        if self._validate_type(obj, value) and self.fvalidate(obj, value):
            obj.Properties[self.name].set_value(value)
            
    def _fvalidate(self, obj, value):
        prop = obj.Properties[self.name]
        if prop.ignore_range:
            return True
        if prop.min is not None and prop.max is not None:
            return value >= prop.min and value <= prop.max            
        return True
        
    def _fformat(self, obj, value):
        return value
        
    def _validate_type(self, obj, value):
        prop = obj.Properties[self.name]
        if self.ignore_type:
            return True
        if value is None:
            return True
        if prop.type is None:
            if value is not None:
                prop.type = type(value)
            return True
        return isinstance(value, prop.type)
        
    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return self.fget(obj)
        
    def __set__(self, obj, value):
        #old = self.fget(obj)
        self.fset(obj, value)
        #if old != value:
        #    obj.Properties[self.name].emit(old=old)
        
class MyWVDict(weakref.WeakValueDictionary):
    def __init__(self, *args, **kwargs):
        self.name = kwargs.get('name')
        del kwargs['name']
        #super(MyWVDict, self).__init__(*args, **kwargs)
        weakref.WeakValueDictionary.__init__(self, *args, **kwargs)
        def remove(wr, selfref=weakref.ref(self)):
            self = selfref()
            if self is not None:
                print 'REMOVE WEAKREF: ', self.name, wr.key
                del self.data[wr.key]
        self._remove = remove

class ObjProperty(object):
    '''This object will be added to an instance of a class that contains a
        ClsProperty.  It is used to store the Property value, min and max settings,
        and handle callbacks.  It also looks at its type and attempts to use
        specialized classes to emulate container types.
        Currently, only list and dict types are supported.
    
    '''
    __slots__ = ('name', 'value', 'min', 'max', 'symbol', 
                 'type', '_type', 'parent_obj', 'quiet', 'weakrefs', '__weakref__', 
                 'threaded', 'ignore_range', 'own_callbacks',  
                 'linked_properties', 'enable_emission', 'queue_emission', 
                 'emission_event', 'emission_threads')
    def __init__(self, **kwargs):
        self.enable_emission = True
        self.queue_emission = False
        self.name = kwargs.get('name')
        self.type = kwargs.get('type')
        self._type = EMULATED_TYPES.get(self.type)
        self.value = kwargs.get('value')
        if self._type is not None:
            self.value = self._type(self.value, parent_property=self)
        self.min = kwargs.get('min')
        self.max = kwargs.get('max')
        self.symbol = kwargs.get('symbol')
        self.parent_obj = kwargs.get('obj')
        self.quiet = kwargs.get('quiet')
        self.ignore_range = kwargs.get('ignore_range')
        self.threaded = kwargs.get('threaded')
        self.own_callbacks = set()
        #self.callbacks = set()
        self.weakrefs = MyWVDict(name='property ' + self.name)
        self.linked_properties = set()
        if self.threaded:
            self.emission_event = threading.Event()
            self.emission_threads = {}
    
    @property
    def range(self):
        return [self.min, self.max]
    @range.setter
    def range(self, value):
        self.min, self.max = value
        
    @property
    def normalized(self):
        if isinstance(self.value, dict):
            d = {}
            for key, val in self.value.iteritems():
                d[key] = val / (self.max[key] - self.min[key])
            return d
        elif isinstance(self.value, list):
            return [v / (self.max[i] - self.min[i]) for i, v in enumerate(self.value)]
        return self.value / (self.max - self.min)
    @normalized.setter
    def normalized(self, value):
        if isinstance(self.value, dict):
            value = value.copy()
            for key in value.iterkeys():
                value[key] = value[key] * (self.max[key] - self.min[key])
            self.set_value(value)
        elif isinstance(self.value, list):
            value = [v * (self.max[i] - self.min[i]) for i, v in enumerate(value)]
            self.set_value(value)
        else:
            self.set_value(value * (self.max - self.min))
    @property
    def normalized_and_offset(self):
        if isinstance(self.value, dict):
            d = self.normalized
            for key in d.iterkeys():
                #d[key] = d[key] + ((self.max[key] - self.min[key]) / 2.)
                d[key] = d[key] - self.min[key]
            return d
        elif isinstance(self.value, list):
            #return [v + ((self.max[i] - self.min[i]) / 2.) for i, v in self.normalized]
            return [v - self.min[i] for i, v in enumerate(self.normalized)]
        return self.normalized - self.min
    @normalized_and_offset.setter
    def normalized_and_offset(self, value):
        if isinstance(self.value, dict):
            value = value.copy()
            for key in value.iterkeys():
                value[key] = (value[key] * (self.max[key] - self.min[key])) + self.min[key]
                #value[key] = value[key] - ((self.max[key] - self.min[key]) / 2.)
            #self.normalized = value
            self.set_value(value)
        elif isinstance(self.value, list):
            value = [(v * (self.max[i] - self.min[i])) + self.min[i] for i, v in enumerate(value)]
            self.set_value(value)
            #value = [v - ((self.max[i] - self.min[i]) / 2.) for i, v in enumerate(value)]
            #self.normalized = value
        else:
            #self.normalized = value - ((self.max - self.min) / 2.)
            self.set_value((value * (self.max - self.min)) + self.min)
        
    def set_value(self, value):
        self.enable_emission = False
        if self._type is not None:
            old = self.value.copy()
            self.value._update_value(value)
        else:
            old = self.value
            self.value = value
        self.enable_emission = True
        
        if old != self.value or self.queue_emission:
            self.emit(old)
        self.queue_emission = False
            
    def bind(self, cb):
        if getattr(cb, 'im_self', None) == self.parent_obj:
            self.own_callbacks.add(cb)
        else:
            wrkey = (cb.im_func, id(cb))
            self.weakrefs[wrkey] = cb.im_self
            
    def old_bind(self, cb):
        if getattr(cb, 'im_self', None) == self.parent_obj:
            self.own_callbacks.add(cb)
        else:
            self.callbacks.add(cb)
            if self.threaded:
                t = ThreadedEmitter(callback=cb, parent_property=self)
                if t.id not in self.emission_threads:
                    self.emission_threads[t.id] = t
                    t.start()
            
    def unbind(self, cb):
        result = False
        if not callable(cb):
            ## Assume this is an instance object and attempt to unlink
            ## any methods that belong to it.
            obj = cb
            found = set()
            for wrkey in self.weakrefs.keys()[:]:
                if self.weakrefs[wrkey] == obj:
                    found.add(getattr(obj, wrkey[0].func_name))
            for realcb in found:
                r = self.unbind(realcb)
                if r:
                    result = True
            return result
        if self.threaded:
            if id(cb) in self.emission_threads:
                t.stop()
                del self.emission_threads[id(cb)]
        found = set()
        for wrkey in self.weakrefs.keys()[:]:
            if id(cb) in wrkey:
                found.add(wrkey)
                result = True
        for wrkey in found:
            del self.weakrefs[wrkey]
        if cb in self.own_callbacks:
            result = True
            self.own_callbacks.discard(cb)
        return result
            
    def old_unbind(self, cb):
        result = False
        if not callable(cb):
            ## Assume this is an instance object and attempt to unlink
            ## any methods that belong to it.
            obj = cb
            found = set()
            for c in self.callbacks:
                if getattr(c, 'im_self', None) == obj:
                    found.add(c)
            for realcb in found:
                r = self.unbind(realcb)
                if r:
                    result = True
            return result
        if self.threaded:
            if id(cb) in self.emission_threads:
                t.stop()
                del self.emission_threads[id(cb)]
        if cb in self.callbacks or cb in self.own_callbacks:
            result = True
        self.callbacks.discard(cb)
        self.own_callbacks.discard(cb)
        return result
        
    def link(self, prop, key=None):
        '''Link this Property to another Property.
        
        '''
        if self.update_linked_property(prop, key):
            self.linked_properties.add((prop, key))
            attrs = ['min', 'max']
            if prop.type == self.type:
                for attr in attrs:
                    setattr(prop, attr, getattr(self, attr))
            elif self._type is not None:
                for attr in attrs:
                    setattr(prop, attr, getattr(self, attr)[key])
            elif prop._type is not None:
                for attr in attrs:
                    pvalue = getattr(prop, attr)
                    pvalue[key] = getattr(self, attr)
            
    def unlink(self, prop, key=None):
        self.linked_properties.discard((prop, key))
        
    def update_linked_property(self, prop, key=None):
        if prop.type == self.type:
            prop.set_value(self.value)
        elif self._type is not None:
            prop.set_value(self.value[key])
        elif prop._type is not None:
            #prop.set_value({key:self.value})
            prop.value[key] = self.value
        else:
            return False
        return True
        
    def emit(self, old):
        if not self.enable_emission:
            self.queue_emission = True
            return
        value = getattr(self.parent_obj, self.name)
        cb_kwargs = dict(name=self.name, Property=self, value=value, old=old, obj=self.parent_obj)
        for cb in self.own_callbacks:
            cb(**cb_kwargs)
        if self.threaded:
            self.emission_event.set()
            self.emission_event.clear()
        else:
            for wrkey in self.weakrefs.keys()[:]:
                f, objID = wrkey
                f(self.weakrefs[wrkey], **cb_kwargs)
            #for cb in self.callbacks.copy():
            #    cb(**cb_kwargs)
            if not self.quiet:
                self.parent_obj.emit('property_changed', **cb_kwargs)
        for prop, key in self.linked_properties:
            self.update_linked_property(prop, key)
            
class ThreadedEmitter(threading.Thread):
    def __init__(self, **kwargs):
        threading.Thread.__init__(self)
        self.callback = kwargs.get('callback')
        self.id = id(self.callback)
        self.parent_property = kwargs.get('parent_property')
        self.running = threading.Event()
        print 'threaded emitter init: ', self.parent_property.name
    def run(self):
        self.running.set()
        while self.running.isSet():
            self.parent_property.emission_event.wait()
            self.do_callback()
        print 'threaded emitter stopped: ', self.parent_property.name
    def do_callback(self):
        if not self.running.isSet():
            return
        cb_kwargs = dict(name=self.parent_property.name, Property=self.parent_property, 
                         obj=self.parent_property.parent_obj, value=self.parent_property.value)
        #print 'threaded emitter: ', cb_kwargs['name'], cb_kwargs['value'], self.name
        self.callback(**cb_kwargs)
    def stop(self):
        self.running.clear()
        self.parent_property.emit(self.parent_property.value)

class ListProperty(list):
    def __init__(self, initlist=None, **kwargs):
        self.parent_property = kwargs.get('parent_property')
        super(ListProperty, self).__init__(initlist)
    def _update_value(self, value):
        for i, item in enumerate(value):
            if i <= len(self):
                if item != self[i]:
                    self[i] = item
            else:
                self.append(item)
    def __setitem__(self, i, item):
        old = self[:]
        list.__setitem__(self, i, item)
        self.parent_property.emit(old)
    def __delitem__(self, i):
        old = self[:]
        list.__delitem__(self, i)
        self.parent_property.emit(old)
    def append(self, *args):
        old = self[:]
        super(ListProperty, self).append(*args)
        self.parent_property.emit(old)
    def insert(self, *args):
        old = self[:]
        super(ListProperty, self).insert(*args)
        self.parent_property.emit(old)
    def pop(self, *args):
        old = self[:]
        super(ListProperty, self).pop(*args)
        self.parent_property.emit(old)
    def remove(self, *args):
        old = self[:]
        super(ListProperty, self).remove(*args)
        self.parent_property.emit(old)
    def extend(self, *args):
        old = self[:]
        super(ListProperty, self).extend(*args)
        self.parent_property.emit(old)
        
class DictProperty(dict):
    def __init__(self, initdict=None, **kwargs):
        self.parent_property = kwargs.get('parent_property')
        super(DictProperty, self).__init__(initdict)
    def _update_value(self, value):
        self.update(value)
    def __setitem__(self, key, item):
        old = self.copy()
        change = self._check_for_change(key, item)
        dict.__setitem__(self, key, item)
        if change:
            self.parent_property.emit(old)
    def __delitem__(self, key):
        old = self.copy()
        dict.__delitem__(self, key)
        self.parent_property.emit(old)
    def clear(self, *args):
        old = self.copy()
        super(DictProperty, self).clear(*args)
        self.parent_property.emit(old)
    def update(self, d):
        for key, val in d.iteritems():
            if self._check_for_change(key, val):
                self.parent_property.queue_emission = True
        super(DictProperty, self).update(d)
    def _check_for_change(self, key, value):
        if key not in self:
            return True
        return value != self[key]
        
EMULATED_TYPES = {list:ListProperty, dict:DictProperty}
    
class PropertyConnector(object):
    '''Mixin for objects to easily connect to Properties.
        Adds a descriptor called 'Property' (a normal python 'property' object)
        that aids in connecting and disconnecting to Property objects.
    :Methods:
        'set_Property_value' : 
        'unlink_Property' : unlinks the current Property.  Don't call directly, 
            instead use 'self.Property = None'.  This can be extended by subclasses
            however to perform functions after a Property is detached.
        'attach_Property' : attaches the given Property.  Don't call directly, 
            instead use 'self.Property = some_Property'.  This can be extended by subclasses
            however to perform functions after a Property is attached.
    :properties:
        'Property' : attaches the given Property object and detaches the current
            one if it exists.  If None is given, it simply detaches.
    '''
    
    @property
    def Property(self):
        if not hasattr(self, '_Property'):
            self._Property = None
        return self._Property
    @Property.setter
    def Property(self, value):
        '''This descriptor attaches the given Property object and detaches
        the current one if it exists.  If None is given, it simply detaches.
        For convenience, a list or tuple can be given with an object and the
        name of the Property and the Property object will be looked up
        (e.g. self.Property = [SomeObject, 'some_property_name'])
        '''
        if type(value) == tuple or type(value) == list:
            obj, propname = value
            value = obj.Properties[propname]            
        if value != self.Property:
            if self.Property is not None:
                self.unlink_Property(self.Property)
            self._Property = value
            if value is not None:
                self.attach_Property(value)
                
    def unlink_Property(self, prop):
        '''unlinks the current Property.  Don't call directly, 
        instead use 'self.Property = None'.  This can be extended by subclasses
        however to perform functions after a Property is detached.
        :Parameters:
            'prop' : Property object
        '''
        prop.unbind(self.on_Property_value_changed)
        
    def attach_Property(self, prop):
        '''attaches the given Property.  Don't call directly, 
        instead use 'self.Property = some_Property'.  This can be extended by 
        subclasses however to perform functions after a Property is attached.
        :Parameters:
            'prop' : Property object
        '''
        prop.bind(self.on_Property_value_changed)
        
    def set_Property_value(self, value, convert_type=False):
        '''Use this method for convenience to set the value of the attached
        Property, if there is one attached.
        :Parameters:
            'value' : the value to set
            'convert_type' : bool, if True, attempts to convert the given
                value to the type associated with the Property. default is False
        '''
        if self.Property is not None:
            if convert_type:
                value = self.Property.type(value)
            setattr(self.Property.parent_obj, self.Property.name, value)
            
    def get_Property_value(self):
        '''Use this method for convenience to get the value of the attached
        Property, if there is one attached.
        '''
        if self.Property is not None:
            return getattr(self.Property.parent_obj, self.Property.name)
            
    def on_Property_value_changed(self, **kwargs):
        '''Override this method to get Property updates.  This is the method
        bound when a Property is attached.
        '''
        pass
