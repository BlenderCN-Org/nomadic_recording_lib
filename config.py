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
        self._confsection = kwargs.get('confsection', self.__class__._confsection)
        self._save_config_file = kwargs.get('_save_config_file', True)
        #self.section = kwargs.get('section')
        #self.items = kwargs.get('items')
        self._confparser = SafeConfigParser()
        self._confparser.read(self._conf_filename)
        if self._confparser.has_section(self._confsection) is False:
            self._confparser.add_section(self._confsection)
            self.write_conf()
    def get_conf(self, key=None, default=None):
        items = dict(self._confparser.items(self._confsection))
        if items is None:
            return default
        for itemkey in items.iterkeys():
            if ',' in items[itemkey]:
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
        for key, val in kwargs.iteritems():
            if type(val) == list or type(val) == tuple:
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
    
    
