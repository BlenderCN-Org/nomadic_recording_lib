import sys
import os.path
import types
import imp

LINKED_PATHS = {}
LOADERS = {}

def add_link(vpath, rpath):
    '''adds virtual module paths via keyword arguments.
    form is virtual_path=real_module_path
    '''
    LINKED_PATHS[vpath] = rpath
    l = LOADERS.get(rpath)
    if l is not None:
        'adding link, found loader. vpath=%s, rpath=%s, loader=%r' % (vpath, rpath, l)

class VirtualModuleLoader(object):
    def __init__(self, name, file, pathname, desc, scope, vpath):
        self.file = file
        self.name = name
        self.pathname = pathname
        self.desc = desc
        self.scope = scope
        self.virtual_path = vpath
        self.real_path = '.'.join(os.path.splitext(self.pathname)[0].split('/'))
    def load_module(self, fullname):
        mod = None
        try:
            mod = sys.modules.get(self.name)
            if not mod:
                mod = sys.modules.get(self.real_path)
            if not mod:
                mod = sys.modules.get(fullname)
            if not mod:
                mod = imp.load_module(self.name, self.file,
                                      self.pathname, self.desc)
            #for vpath in self.virtual_paths:
            #    mod.__path__.append(vpath)
            sys.modules[fullname] = mod
            if self.virtual_path is not None:
                sys.modules[self.virtual_path] = mod
        finally:
            if self.file:
                self.file.close()
        return mod
    def __repr__(self):
        s = '<VirtualModuleLoader:'
        for key in ['name', 'file', 'pathname', 'desc', 'virtual_path', 'real_path']:
            val = getattr(self, key)
            s += ' %s=%s' % (key, val)
        s += '>'
        return s
        
class VirtualModuleFinder(object):
    @staticmethod
    def _search_links(fullname, path):
        scope = sys._getframe(2).f_globals
        #current_path = '.'.join(scope['__name__'].split('.')[:-1])
        current_path = scope['__name__']
        if '.' in fullname:
            head, fullname = fullname.rsplit('.', 1)
        searchpath = '.'.join([current_path, fullname])
#        if fullname == 'bases':
#            print 'searching: current_path=%s, fullname=%s, searchpath=%s, result=%s' % (current_path, fullname, searchpath, LINKED_PATHS.get(searchpath))
#            keys = ['name', 'file', 'package']
#            print dict(zip(keys, [scope.get(key.join(['__']*2)) for key in keys]))
        return LINKED_PATHS.get(searchpath)
    @staticmethod
    def _search_links_rev(fullname):
        found = []
        for key, val in LINKED_PATHS.iteritems():
            if val == fullname:
                found.append(key)
        return found
        
    def find_module(self, fullname, path=None):
        real_name = fullname
        searchpath = self._search_links(fullname, path)
        if searchpath is not None:
            #return DynamicNamespaceLoader(fullname)
            fullname = searchpath
        origName = fullname
        
        if not path:
            mod = sys.modules.get(fullname, False)
            if mod is None or mod and isinstance(mod, types.ModuleType):
                return mod
        frame = sys._getframe(1)
        global_scope = frame.f_globals
        
        if '.' in fullname:
            head, fullname = fullname.rsplit('.', 1)
            mod = sys.modules.get(head,None)
            if mod is None:
                return None
            if hasattr(mod, '__path__'):
                path = mod.__path__
        try:
            l = LOADERS.get(real_name)
            if l is None:
                l = LOADERS.get(origName)
            if l is not None:
                #print 'using existing loader: %s' % (l)
                return l
            file, pathname, desc = imp.find_module(fullname, path)
            if True:#searchpath is not None:
                loader = VirtualModuleLoader(origName, file, pathname, desc, global_scope, real_name)
                LOADERS[loader.name] = loader
                if searchpath is not None:
                    LOADERS[searchpath] = loader
                    #print 'searchpath %s loader added: %r' % (searchpath, loader)
                
                return loader
            else:
                return None
        except ImportError:
            return None
        
sys.meta_path.append(VirtualModuleFinder())
