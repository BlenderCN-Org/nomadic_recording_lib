import os.path
import datetime
import tarfile
from cStringIO import StringIO
import UserDict
import jsonpickle
if jsonpickle.__version__ != '0.3.1':
    raise

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

def build_datetime_string(fmt_str, dt=None):
    if dt is None:
        dt = datetime.datetime.now()
        
    
class FileSection(object):
    def init_filesection(self, **kwargs):
        if not hasattr(self, 'filesection_path'):
            self.filesection_path = kwargs.get('filesection_path', '/')
        if not hasattr(self, 'filesection_filename'):
            self.filesection_filename = kwargs.get('filesection_filename')
        if not hasattr(self, 'filesection_datetime_format'):
            self.filesection_datetime_format = '%Y%m%d-%H:%M:%S'
        attrs = ['file_created', 'file_modified']
        self.saved_attributes |= set(attrs)
        for attr in attrs:
            if not hasattr(self, attr):
                setattr(self, attr, None)
        self.filesection_initialized = True
        
    @property
    def filesection_tarname(self):
        self.filesection_check_init()
        return os.path.join(self.filesection_path, self.filesection_filename)
        
    def filesection_check_init(self):
        if not getattr(self, 'filesection_initialized', False):
            self.init_filesection()
        
    def filesection_open_archive(self, filename, mode):
        self.filesection_check_init()
        tar = tarfile.open(filename, mode)
        return tar
        
    def filesection_build_file(self, tar, **kwargs):
        self.filesection_check_init()
        if self.file_created is None:
            self.file_created = build_datetime_string(self.filesection_datetime_format)
            self.file_modified = self.file_created
        if self.file_modified is None:
            self.file_modified = build_datetime_string(self.filesection_datetime_format)
        js = self.to_json(**kwargs)
        tinf = tarfile.TarInfo(self.filesection_tarname)
        sio = StringIO(js)
        tar.addfile(tinf, fileobj=sio)
        #sio.close()
        
    def filesection_load_file(self, tar, **kwargs):
        self.filesection_check_init()
        js = ''
        file = tar.extractfile(self.filesection_tarname)
        for line in file:
            js += line
        file.close()
        self.from_json(js)
        
