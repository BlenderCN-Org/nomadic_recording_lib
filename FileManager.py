import os.path
import datetime
import mimetypes

from BaseObject import BaseObject
from config import Config


class FileManager(BaseObject, Config):
    _confsection = 'FileManager'
    datetime_fmt = '%Y%m%d_%H%M%S%f'
    max_recent_files = 10
    _Properties = {'current_file':dict(type=str)}
    def __init__(self, **kwargs):
        BaseObject.__init__(self, **kwargs)
        Config.__init__(self, **kwargs)
        self._mimetypes = mimetypes.MimeTypes()
        self.filetypes = {}
        filetype_data = kwargs.get('filetype_data', [])
        for data in filetype_data:
            self.add_filetype(**data)
        self.recent_files = {}
        self.files_by_path = {}
        self.get_recent_files()
        self.bind(current_file=self._on_current_file_set)
        
    @property
    def most_recent_file(self):
        if not len(self.recent_files):
            return None
        return self.recent_files[max(self.recent_files.keys())]
    @property
    def most_recent_dir(self):
        file = self.most_recent_file
        if not file:
            return
        return os.path.dirname(file)
    
    def load_file(self, **kwargs):
        filename = kwargs.get('filename')
        ft = self.guess_filetype(filename)
        if ft:
            ft.load(**kwargs)
            if ft.is_main_filetype:
                self.current_file = filename
        
    def save_file(self, **kwargs):
        filename = kwargs.get('filename')
        ft = self.guess_filetype(filename)
        if ft:
            ft.save(**kwargs)
            if ft.is_main_filetype:
                self.current_file = filename
        
    def save_current(self):
        if self.current_file is not None:
            self.save_file(filename=self.current_file)
            return True
        return False
        
    def close_file(self):
        self.current_file = None
            
    def guess_filetype(self, filename):
        r, ext = os.path.splitext(filename)
        return self.filetypes.get(ext)
            
    def _on_current_file_set(self, **kwargs):
        filename = kwargs.get('value')
        if filename is not None:
            self.add_file(filename)
            
    def add_file(self, file):
        now = datetime.datetime.now()
        old = self.files_by_path.get(file)
        if old is not None:
            del self.recent_files[old]
        self.recent_files[now] = file
        self.files_by_path[file] = now
        self.update_recent_files()
        
    def update_recent_files(self):
        self.remove_old_files()
        self.remove_invalid_files()
        self.remove_conf_options()
        for dt in reversed(sorted(self.recent_files.keys())):
            file = self.recent_files[dt]
            s = dt.strftime(self.datetime_fmt)
            self.update_conf(**{s:file})
        
    def get_recent_files(self):
        d = self.get_conf()
        for s, file in d.iteritems():
            dt = datetime.datetime.strptime(s, self.datetime_fmt)
            self.recent_files[dt] = file
            self.files_by_path[file] = dt
        self.remove_invalid_files()
        self.remove_old_files()
        
    def remove_old_files(self):
        if len(self.recent_files) > self.max_recent_files:
            removed = []
            keys = sorted(self.recent_files.keys())
            keys.reverse()
            for key in keys[self.max_recent_files:]:
                file = self.recent_files[key]
                dt = self.files_by_path.get(file)
                if dt == key:
                    del self.files_by_path[file]
                del self.recent_files[key]
                removed.append(dt.strftime(self.datetime_fmt))
            if len(removed):
                self.remove_conf_options(removed)
        
    def remove_invalid_files(self):
        dead = set()
        for dt, file in self.recent_files.iteritems():
            if not os.path.exists(file):
                dead.add(dt)
            if len(self.filetypes) and self.guess_filetype(file) is None:
                dead.add(dt)
        if not len(dead):
            return
        self.remove_conf_options([dt.strftime(self.datetime_fmt) for dt in dead])
        for dt in dead:
            file = self.recent_files[dt]
            del self.files_by_path[file]
            del self.recent_files[dt]
        
    def add_filetype(self, **kwargs):
        ft = FileType(**kwargs)
        if ft.mimetype:
            self._mimetypes.add_type(ft.extension, ft.mimetype)
        else:
            mtype, enc = self._mimetypes.guess_type('test' + ft.extension)
            if mtype is not None:
                ft.mimetype = mtype
        self.filetypes[ft.id] = ft
        return ft

class FileType(object):
    def __init__(self, **kwargs):
        self.extension = kwargs.get('extension')
        self.description = kwargs.get('description', '')
        self.mimetype = kwargs.get('mimetype', '')
        self.is_main_filetype = kwargs.get('is_main_filetype', True)
        self.load_callback = kwargs.get('load_callback')
        self.save_callback = kwargs.get('save_callback')
    @property
    def id(self):
        return self.extension
    def load(self, **kwargs):
        if self.load_callback is not None:
            self.load_callback(**kwargs)
    def save(self, **kwargs):
        if self.save_callback is not None:
            self.save_callback(**kwargs)
