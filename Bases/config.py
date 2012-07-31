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
# config.py
# Copyright (c) 2010 - 2011 Matthew Reid

import sys
import os
import threading
from ConfigParser import SafeConfigParser
from BaseObject import GLOBAL_CONFIG

#default_conf = os.path.expanduser('~/.openlightingdesigner.conf')
def build_conf_filename():
    cfilename = GLOBAL_CONFIG.get('conf_filename')
    if cfilename:
        return cfilename
    app = GLOBAL_CONFIG.get('app_name')
    if app is None:
        return False
        #app = sys.argv[0].split('.py')[0]
    return os.path.expanduser('~/.%s.conf' % (app))

class Config(object):
    def __init__(self, **kwargs):
        _conf_filename = kwargs.get('_conf_filename', build_conf_filename())
        self._confsection = kwargs.get('confsection', getattr(self.__class__, '_confsection', None))
        self._save_config_file = kwargs.get('_save_config_file', True)
        self._confparser = SafeConfigParser()
        self.set_conf_filename(_conf_filename)
        GLOBAL_CONFIG.bind(update=self._CONF_ON_GLOBAL_CONFIG_UPDATE)
    def set_conf_filename(self, filename):
        self._conf_filename = filename
        self._read_conf_file()
        if self._confsection is None:
            return
        if self._confparser.has_section(self._confsection) is False:
            self._confparser.add_section(self._confsection)
    def _read_conf_file(self):
        if not self._conf_filename:
            return
        self._confparser.read(self._conf_filename)
    def get_conf(self, key=None, default=None):
        self._read_conf_file()
        if self._confsection is None:
            return {}
        items = dict(self._confparser.items(self._confsection))
        if items is None:
            return default
        for itemkey in items.iterkeys():
            value = items[itemkey]
            dict_chars = '{:}'
            if False not in [c in items[itemkey] for c in dict_chars]:
                ## a possible dictionary repr
                try:
                    d = eval(items[itemkey])
                    items[itemkey] = d
                except:
                    pass
            elif ',' in items[itemkey]:
                items[itemkey] = items[itemkey].split(',')
        if key is not None:
            return items.get(key, default)
        return items
    def update_conf(self, **kwargs):
        self._read_conf_file()
        for key, val in kwargs.iteritems():
            if isinstance(val, list) or isinstance(val, tuple):
                slist = [str(element) for element in val]
                if len(slist) == 1:
                    s = slist[0] + ','
                else:
                    s = ','.join(slist)
            else:
                s = str(val)
            self._confparser.set(self._confsection, key, s)
        self.write_conf()
    def remove_conf_options(self, options=None):
        self._read_conf_file()
        items = dict(self._confparser.items(self._confsection))
        if options is None:
            options = items.keys()
        for option in options:
            if option not in items:
                continue
            self._confparser.remove_option(self._confsection, option)
        self.write_conf()
    def write_conf(self):
        if not self._conf_filename:
            return
        if not self._save_config_file:
            return
        file = open(self._conf_filename, 'w')
        self._confparser.write(file)
        file.close()
    def _CONF_ON_GLOBAL_CONFIG_UPDATE(self, **kwargs):
        cfilename = build_conf_filename()
        if cfilename == self._conf_filename:
            return
        self.set_conf_filename(cfilename)
    
class ConfParserBase(object):
    _conf_data_needed = []
    def __init__(self, **kwargs):
        self.items = {}
        self._conf_data = {}
        self.conf_source = None
        self.set_conf_data(kwargs.get('conf_data', {}))
        
    @property
    def is_conf_valid(self):
        if self.conf_source is None:
            return False
        return None not in [self._conf_data.get(key) for key in self._conf_data_needed]
    def set_conf_data(self, d):
        self._conf_data.update(d)
        fn = d.get('filename')
        skwargs = {}
        if fn is not None:
            skwargs['type'] = FilenameConfSource
            skwargs['filename'] = fn
        self.set_conf_source(**skwargs)
    def set_conf_source(self, **kwargs):
        if self.conf_source is not None:
            self.conf_source.close()
            self.conf_source = None
        cls = kwargs.get('type')
        if cls is None:
            return
        self.conf_source = cls(**kwargs)
    def get_conf(self, key=None, default=None):
        items = self._get_conf_items()
        if not items or key not in items:
            return default
        if key is not None:
            return items.get(key, default)
        return items
    def update_conf(self, **kwargs):
        items = self._get_conf_items()
        for key, val in kwargs.iteritems():
            self._do_set_item(key, val)
        self.write_source()
    def remove_conf_items(self, options=None):
        items = self._get_conf_items()
        if options is None:
            options = items.keys()
        for key in options:
            if key not in items:
                continue
            self._do_remove_item(key)
        self.write_source()
    def _get_conf_items(self):
        return self.items
    def read_source(self):
        pass
    def write_source(self):
        pass
    def _do_set_item(self, key, value):
        self.items[key] = value
    def _do_remove_item(self, key):
        if key in self.items:
            del self.items[key]
            
class ConfParserINI(ConfParserBase):
    _conf_data_needed = ['section']
    def __init__(self, **kwargs):
        self._parser = SafeConfigParser()
        super(ConfParserINI, self).__init__(**kwargs)
    def set_conf_data(self, d):
        super(ConfParserINI, self).set_conf_data(d)
        if not self.is_conf_valid:
            return
        #self._parser.read(d['filename'])
        self.read_source()
        if not self._parser.has_section(d['section']):
            self._parser.add_section(d['section'])
    def _do_set_item(self, key, val):
        dict_chars = '{:}'
        if False not in [c in val for c in dict_chars]:
            ## a possible dictionary repr
            try:
                d = eval(val)
                #items[itemkey] = d
                val = d
            except:
                pass
        elif ',' in val:
            val = val.split(',')
        self.items[key] = val
        if not self.is_conf_valid:
            return
        section = self._conf_data.get('section')
        if section is None:
            return
        self._parser.set(section, key, val)
    def _format_item(self, val):
        if isinstance(val, list) or isinstance(val, tuple):
            slist = [str(element) for element in val]
            if len(slist) == 1:
                s = slist[0] + ','
            else:
                s = ','.join(slist)
        else:
            s = str(val)
        return s
    def _get_conf_items(self):
        if not self.is_conf_valid:
            return super(ConfParserINI, self)._get_conf_items()
        d = self._conf_data
        self.read_source()
        #self._parser.read(d['filename'])
        items = dict(self._parser.items(d['section']))
        for key in items.keys()[:]:
            val = self._format_item(items[key])
            items[key] = val
        self.items.update(items)
        return self.items
    def read_source(self):
        if not self.is_conf_valid:
            return
        src = self.conf_source
        with src:
            self._parser.readfp(src.fp)
    def write_source(self, fp):
        if not self.is_conf_valid:
            return
        src = self.conf_source
        with src:
            self._parser.write(src.fp)
        #file = open(self._conf_data['filename'], 'w')
        #self._parser.write(file)
        #file.close()
        
class BaseConfSource(object):
    def __init__(self, **kwargs):
        self._fp_open = threading.Event()
        self._fp_closed = threading.Event()
        self._fp_closed.set()
        self.fp = None
    def build_fp(self, *args, **kwargs):
        pass
    def close_fp(self):
        pass
    def open(self):
        self._fp_closed.wait()
        self.fp = self.build_fp()
        self._fp_closed.clear()
        self._fp_open.set()
    def close(self):
        if self.fp is not None:
            self.close_fp()
            self.fp = None
        self._fp_open.clear()
        self._fp_closed.set()
    def __enter__(self):
        self.open()
    def __exit__(self, *args):
        self.close()
        
        
class FilenameConfSource(BaseConfSource):
    def __init__(self, **kwargs):
        self.filename = kwargs.get('filename')
    def build_fp(self):
        return open(self.filename, 'rw')
    def close_fp(self):
        self.fp.close()
    
