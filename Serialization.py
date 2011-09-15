import UserDict
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
        jsonpickle.set_encoder_options('simplejson', **json_presets[json_preset])
        return jsonpickle.encode(d, unpicklable=False)
        
    def from_json(self, string, **kwargs):
        d = jsonpickle.decode(string)
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
            for realtype, emutype in EMULATED_TYPES.iteritems():
                if isinstance(val, emutype):
                    val = realtype(val)
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
