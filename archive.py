import os.path
import time
import datetime
import tarfile
from StringIO import StringIO

import jsonpickle

from BaseObject import BaseObject
from Serialization import json_presets


def build_datetime_string(fmt_str, dt=None):
    if dt is None:
        dt = datetime.datetime.now()
    return dt.strftime(fmt_str)
    
def parse_datetime_string(s, fmt_str):
    return datetime.datetime.strptime(s, fmt_str)

class ArchiveMember(BaseObject):
    _saved_class_name = 'ArchiveMember'
    _saved_attributes = ['filename', 'file_created', 'file_modified']
    def __init__(self, **kwargs):
        super(ArchiveMember, self).__init__(**kwargs)
        self.saved_attributes.discard('Index')
        self.name = kwargs.get('name')
        self.path = kwargs.get('path', '/')
        self.filename = kwargs.get('filename')
        self.id = kwargs.get('id', self.full_path)
        self.serialize_obj = kwargs.get('serialize_obj', {})
        self.serialize_kwargs = kwargs.get('serialize_kwargs', {})
        self.deserialize_kwargs = kwargs.get('deserialize_kwargs', {})
        self.datetime_format = kwargs.get('datetime_format', '%Y%m%d-%H:%M:%S')
        self.json_preset = kwargs.get('json_preset', 'pretty')
        self.file_created = None
        self.file_modified = None
        
    @property
    def full_path(self):
        return os.path.join(self.path, self.filename)
        
    def save(self):
        if self.file_created is None:
            self.file_created = build_datetime_string(self.datetime_format)
            self.file_modified = self.file_created
        if self.file_modified is None:
            self.file_modified = build_datetime_string(self.datetime_format)
        file = StringIO(self._serialize())
        file.seek(0)
        tinf = tarfile.TarInfo(self.full_path)
        tinf.size = len(file.buf)
        dt = parse_datetime_string(self.file_modified, self.datetime_format)
        tinf.mtime = time.mktime(dt.timetuple())
        return file, tinf
        
    def load(self, tar):
        js = ''
        try:
            tinf = tar.getmember(self.full_path)
            file = tar.extractfile(tinf)
        except KeyError:
            return
        for line in file:
            js += line
        file.close()
        d = jsonpickle.decode(js)
        self._load_saved_attr(d)
        for key, objdict in d['serialize_obj'].iteritems():
            obj = self.serialize_obj.get(key)
            if not obj:
                continue
            dskwargs = self.deserialize_kwargs.get(key, {})
            obj._load_saved_attr(objdict, **dskwargs)
        
    def _serialize(self):
        d = self._get_saved_attr()
        d['serialize_obj'] = {}
        for key, obj in self.serialize_obj.iteritems():
            skwargs = self.serialize_kwargs.get(key, {})
            d['serialize_obj'][key] = obj._get_saved_attr(**skwargs)
        jsonpickle.set_encoder_options('simplejson', **json_presets[self.json_preset])
        return jsonpickle.encode(d, unpicklable=False)
        

class Archive(BaseObject):
    _ChildGroups = {'members':{'child_class':ArchiveMember}}
    def __init__(self, **kwargs):
        super(Archive, self).__init__(**kwargs)
        
    def add_member(self, **kwargs):
        self.members.add_child(**kwargs)
        
    def save(self, filename, members=None):
        if members is None:
            members = self.members.keys()
        tar = tarfile.open(filename, 'w:gz')
        files = []
        for key in members:
            member = self.members[key]
            file, tinf = member.save()
            files.append(file)
            tar.addfile(tinf, fileobj=file)
        tar.close()
        for file in files:
            file.close()
            
    def load(self, filename, members=None):
        if members is None:
            members = [self.members.indexed_items[i].id for i in sorted(self.members.indexed_items.keys())]
        tar = tarfile.open(filename, 'r:gz')
        for key in members:
            self.members[key].load(tar)
        tar.close()
        
