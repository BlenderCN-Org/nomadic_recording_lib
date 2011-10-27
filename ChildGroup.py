import UserDict
from osc_base import OSCBaseObject

class ChildGroup(OSCBaseObject, UserDict.UserDict):
    _saved_class_name = 'ChildGroup'
    _Properties = {'name':dict(type=str)}
    def __init__(self, **kwargs):
        name = kwargs.get('name')
        if name:
            kwargs.setdefault('osc_address', name)
        OSCBaseObject.__init__(self, **kwargs)
        self.name = kwargs.get('name')
        self.register_signal('child_added', 'child_removed', 'child_index_changed', 'child_update')
        self.child_class = kwargs.get('child_class')
        self.ignore_index = kwargs.get('ignore_index', False)
        
        UserDict.UserDict.__init__(self)
        self.indexed_items = {}
        
    def add_child(self, cls=None, **kwargs):
        def do_add_child(child):
            self.update({child.id:child})
            if not self.ignore_index:
                self.indexed_items.update({child.Index:child})
                child.bind(Index=self.on_child_Index_changed)
            self.emit('child_added', ChildGroup=self, obj=child)
            self.emit('child_update', ChildGroup=self, mode='add', obj=child)
            return child
            
        child = kwargs.get('existing_object')
        if child is not None:
            if child.id in self:
                return
            if not self.ignore_index:
                index = child.Index
                if index is None:
                    index = kwargs.get('Index', self.find_max_index() + 1)
                if not self.check_valid_index(index):
                    print 'Index error, could not add child ', self.name, child
                    return False
                child.Index = index
            child.ChildGroup_parent = self
            return do_add_child(child)
            
        c_kwargs = kwargs.copy()
        if self.osc_enabled:
            c_kwargs.update({'osc_parent_node':self.osc_node})
        c_kwargs.update({'ChildGroup_parent':self})
        if not self.ignore_index:
            index = kwargs.get('Index', self.find_max_index() + 1)
            if not self.check_valid_index(index):
                return
            c_kwargs['Index'] = index
        if cls is None:
            cls = self.child_class
        child = cls(**c_kwargs)
        return do_add_child(child)
        
    def del_child(self, child):
        if child.id in self:
            del self[child.id]
        if not self.ignore_index:
            child.unbind(self.on_child_Index_changed)
        if child.Index in self.indexed_items:
            del self.indexed_items[child.Index]
        child.unlink()
        self.emit('child_removed', ChildGroup=self, obj=child, id=child.id)
        self.emit('child_update', ChildGroup=self, mode='remove', obj=child)
            
    def get(self, key):
        if type(key) == int and not self.ignore_index:
            return self.indexed_items.get(key)
        return super(ChildGroup, self).get(key)
        
    def find_max_index(self):
        if len(self) == 0:
            return 0
        return max(self.indexed_items.keys())
        
    def check_valid_index(self, index):
        if self.ignore_index:
            return True
        return type(index) == int and index not in self.indexed_items
        
    def clear(self):
        for c in self.values()[:]:
            self.del_child(c)
            #c.unbind(self.on_child_Index_changed)
        #self.indexed_items.clear()
        super(ChildGroup, self).clear()
        
    def on_child_Index_changed(self, **kwargs):
        obj = kwargs.get('obj')
        old = kwargs.get('old')
        value = kwargs.get('value')
        if old is not None and old in self.indexed_items:
            del self.indexed_items[old]
        if value is not None:
            self.indexed_items[value] = obj
        self.emit('child_index_changed', ChildGroup=self, obj=obj, old=old, value=value)
        self.emit('child_update', ChildGroup=self, mode='Index', obj=obj, old=old, value=value)
        
    def unbind_all(self, *args):
        self.unbind(*args)
        for child in self.itervalues():
            child.unbind(*args)
