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
# Serialization.py
# Copyright (c) 2010 - 2011 Matthew Reid

try:
    import UserDict
except:
    import collections as UserDict
import jsonpickle

from Properties import EMULATED_TYPES

json_presets = {'tiny':{'sort_keys':True, 'indent':None, 'separators':(',', ':')}, 
                'pretty':{'sort_keys':True, 'indent':3, 'separators':(', ', ':')}}

class Serializer(object):
    def __init__(self, **kwargs):
        d = kwargs.get('deserialize')
        if d:
            self._load_saved_attr(d)
            for key in self.saved_attributes:
                if not hasattr(self, key):
                    setattr(self, key, None)
            for key in self.saved_child_objects:
                if not hasattr(self, key):
                    setattr(self, key, {})
                    
    def to_json(self, incl_dict={}, **kwargs):
        json_preset = kwargs.get('json_preset', 'tiny')
        if 'json_preset' in kwargs:
            del kwargs['json_preset']
        d = self._get_saved_attr(**kwargs)
        d.update(incl_dict)
        return to_json(d, json_preset)
        
    def from_json(self, string, **kwargs):
        d = from_json(string)
        self._load_saved_attr(d, **kwargs)
        
    def _get_saved_attr(self, **kwargs):
        saved_child_objects = kwargs.get('saved_child_objects')
        if saved_child_objects is not None:
            del kwargs['saved_child_objects']
        d = {}
        d.update({'saved_class_name':self.saved_class_name})
        d.update({'attrs':{}})
        for key in self.saved_attributes:
            val = getattr(self, key, None)
            d['attrs'].update({key:val})
        if hasattr(self, 'saved_child_objects'):
            d.update({'saved_children':{}})
            if saved_child_objects is None:
                saved_child_objects = self.saved_child_objects
            for attr in saved_child_objects:
                child_dict = getattr(self, attr)
                if isinstance(child_dict, dict) or isinstance(child_dict, UserDict.UserDict):
                    d['saved_children'].update({attr:{}})
                    for key, val in child_dict.iteritems():
                        if isinstance(val, dict):
                            d['saved_children'][attr].update({key:{}})
                            for dkey, dval in val.iteritems():
                                saved = dval._get_saved_attr(**kwargs)
                                if saved is not False:
                                    d['saved_children'][attr][key].update({dkey:saved})
                        else:
                            saved = val._get_saved_attr(**kwargs)
                            if saved is not False:
                                d['saved_children'][attr].update({key:saved})
                else:
                    saved = child_dict._get_saved_attr(**kwargs)
                    if saved is not False:
                        d['saved_children'].update({attr:saved})
        return d
        
    def _load_saved_attr(self, d, **kwargs):
        if 'saved_class_name' in d:
            self.saved_class_name = d['saved_class_name']
        for key, val in d.get('attrs', {}).iteritems():
            if key in self.saved_attributes:
                setattr(self, key, val)
        if 'saved_children' in d:
            keys = kwargs.get('saved_child_objects', d['saved_children'].keys())
            for key in keys:
                val = d['saved_children'].get(key)
                if val:
                    if type(val) == dict:
                        if hasattr(self, key):
                            cdict = getattr(self, key)
                        else:
                            cdict = {}
                            setattr(self, key, cdict)
                        for ckey, cval in val.iteritems():
                            child = self._deserialize_child(cval)
                            if child and ckey not in cdict:
                                cdict.update({ckey:child})
                    else:
                        obj = self._deserialize_child(val)
                        if obj:
                            setattr(self, key, obj)
                            
    def _deserialize_child(self, d):
        name = d.get('saved_class_name')
        for cls in self.saved_child_classes:
            if cls._saved_class_name == name:
                return cls(deserialize=d)
        return False

def to_json(obj, json_preset='tiny'):
    jsonpickle.set_encoder_options('simplejson', **json_presets[json_preset])
    pickler = Pickler(unpicklable=True)
    return jsonpickle.json.encode(pickler.flatten(obj))
    
def from_json(jstring):
    return jsonpickle.decode(jstring)
    
class Pickler(jsonpickle.Pickler):
    def flatten(self, obj):
        for realtype, emutype in EMULATED_TYPES.iteritems():
            if isinstance(obj, emutype):
                #print 'changed %s to %s' % (emutype, realtype)
                obj = realtype(obj)
                break
        return super(Pickler, self).flatten(obj)
