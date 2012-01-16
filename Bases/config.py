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

import os
from ConfigParser import SafeConfigParser
from BaseObject import GLOBAL_CONFIG

#default_conf = os.path.expanduser('~/.openlightingdesigner.conf')
def build_conf_filename():
    app = GLOBAL_CONFIG['app_name']
    return os.path.expanduser('~/.%s.conf' % (app))

class Config(object):
    def __init__(self, **kwargs):
        self._conf_filename = kwargs.get('_conf_filename', build_conf_filename())
        self._confsection = kwargs.get('confsection', getattr(self.__class__, '_confsection', None))
        self._save_config_file = kwargs.get('_save_config_file', True)
        #self.section = kwargs.get('section')
        #self.items = kwargs.get('items')
        self._confparser = SafeConfigParser()
        self._read_conf_file()
        if self._confparser.has_section(self._confsection) is False:
            self._confparser.add_section(self._confsection)
            self.write_conf()
    def _read_conf_file(self):
        self._confparser.read(self._conf_filename)
    def get_conf(self, key=None, default=None):
        self._read_conf_file()
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
#                s = items[itemkey].split('{')[1]
#                s = s.split('}')[0]
#                if ',' not in s:
#                    s += ','
#                d = {}
#                for ditem in s.split(','):
#                    if ':' not in ditem:
#                        continue
#                    dkey, dval = ditem.split(':')
#                    d[dkey] = dval
#                items[itemkey] = d
            elif ',' in items[itemkey]:
                items[itemkey] = items[itemkey].split(',')
#        for itemkey in items.iterkeys():
#            item = items[itemkey]
#            if '"' in item:
#                items[itemkey] = item.strip('"')
#            elif item != '':
#                items[itemkey] = int(item)
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
            #if type(val) == str:
            #    s = '"' + s + '"'
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
        if self._save_config_file:
            file = open(self._conf_filename, 'w')
            self._confparser.write(file)
            file.close()

class TestConf(Config):
    _confsection = 'TEST'
    
if __name__ == '__main__':
    c = TestConf(_conf_filename='test.conf')
    c.update_conf(testitem='blah')
    c.update_conf(testlist=['blah','stuff'])
    print c.get_conf('testitem')
    print c.get_conf('testlist')
    
    
