import sys
import types
import imp

LINKED_PATHS = {}

def add_link(vpath, rpath):
    '''adds virtual module paths via keyword arguments.
    form is virtual_path=real_module_path
    '''
    LINKED_PATHS[vpath] = rpath

class VirtualModuleLoader(object):
    def __init__(self, name, file, pathname, desc, scope):
        self.file = file
        self.name = name
        self.pathname = pathname
        self.desc = desc
        self.scope = scope
    def load_module(self, fullname):
        mod = None
        try:
            mod = sys.modules.get(self.name)
            if not mod:
                mod = sys.modules.get(fullname)
            if not mod:
                mod = imp.load_module(self.name, self.file,
                                      self.pathname, self.desc)
            sys.modules[fullname] = mod
        finally:
            if self.file:
                self.file.close()
        return mod
        
class VirtualModuleFinder(object):
    def _search_links(self, fullname, path):
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
        
    def find_module(self, fullname, path=None):
        searchpath = self._search_links(fullname, path)
        #if 'bases' in fullname:
        #    print 'vmodulefinder find_module: ', fullname, path, searchpath
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
            file, pathname, desc = imp.find_module(fullname, path)
            return VirtualModuleLoader(origName, file, pathname, desc, global_scope)
        except ImportError:
            return None
        
sys.meta_path.append(VirtualModuleFinder())
