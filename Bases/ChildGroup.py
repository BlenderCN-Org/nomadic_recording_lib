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
# ChildGroup.py
# Copyright (c) 2010 - 2011 Matthew Reid

try:
    import UserDict
except:
    import collections as UserDict
from osc_base import OSCBaseObject

class ChildGroup(OSCBaseObject, UserDict.UserDict):
    _saved_class_name = 'ChildGroup'
    _IsChildGroup_ = True
    _Properties = {'name':dict(type=str)}
    _saved_attributes = ['name', 'ignore_index']
    _saved_child_objects = ['indexed_items']
    def __init__(self, **kwargs):
        UserDict.UserDict.__init__(self)
        self.indexed_items = {}
        self.child_class = kwargs.get('child_class')
        self.deserialize_callback = kwargs.get('deserialize_callback')
        self.parent_obj = kwargs.get('parent_obj')
        name = kwargs.get('name')
        if name:
            kwargs.setdefault('osc_address', name)
        OSCBaseObject.__init__(self, **kwargs)
        self.register_signal('child_added', 'child_removed', 'child_index_changed', 'child_update')
        if 'deserialize' not in kwargs:
            self.name = kwargs.get('name')
            self.ignore_index = kwargs.get('ignore_index', False)
        
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
                    self.LOG.warning('Index error: could not add child', self.name, child)
                    return False
                child.Index = index
            child.ChildGroup_parent = self
            return do_add_child(child)
            
        c_kwargs = kwargs.copy()
        if self.osc_enabled:
            c_kwargs.update({'osc_parent_node':self.osc_node})
        c_kwargs.update({'ChildGroup_parent':self})
        if not self.ignore_index:
            try:
                index = kwargs.get('Index', self.find_max_index() + 1)
            except:
                print self.indexed_items
                raise
            if not self.check_valid_index(index):
                return
            c_kwargs['Index'] = index
        if cls is None:
            cls = self.child_class
        if self.parent_obj is not None:
            cls, c_kwargs = self.parent_obj.ChildGroup_prepare_child_instance(self, cls, **c_kwargs)
        if cls is None:
            return
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
        if len(self) ==0 or len(self.indexed_items) == 0:
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
            
    def _load_saved_attr(self, d, **kwargs):
        if 'saved_class_name' not in d:
            newd = self._get_saved_attr()
            items = {}
            for key, val in d.iteritems():
                i = val['attrs']['Index']
                items[i] = val
            newd['saved_children'] = {'indexed_items':items}
            d = newd
        items = d['saved_children']['indexed_items']
        for key in items.keys()[:]:
            if type(key) != int:
                items[int(key)] = items[key]
                del items[key]
        if self._saved_class_name == 'CategoryPaletteGroup':
            print 'CategoryPaletteGroup load_attr: ', d, kwargs
        super(ChildGroup, self)._load_saved_attr(d, **kwargs)
        
    def _deserialize_child(self, d, **kwargs):
        #print 'ChildGroup deserialize child: ', kwargs, d
        key = kwargs.get('key')
        if d['saved_class_name'] == 'CategoryPalette':
            print 'ChildGroup deserialize palette: ', key, key in self, d
        i = d['attrs']['Index']
        if self.deserialize_callback is not None:
            obj = self.deserialize_callback(d)
            ckwargs = dict(existing_object=obj)
            if True:#obj.Index is None:
                ckwargs['Index'] = i
            self.add_child(**ckwargs)
        elif key is not None and key in self:
            obj = self[key]
            print 'ChildGroup load_attr for child: ', obj, d
            obj._load_saved_attr(d)
        else:
            obj = self.add_child(Index=i, deserialize=d)
            #obj = super(ChildGroup, self)._deserialize_child(d, **kwargs)
        return obj
