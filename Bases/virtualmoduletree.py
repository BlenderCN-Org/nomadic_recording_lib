import sys
import site
import os.path
import types
import imp

LINKED_PATHS = {}
LINKED_MODULES = {}
LOADERS = {}

system_prefixes = site.PREFIXES[:] + [site.USER_SITE]

def add_linked_package(vpath, pkg, submodule_names=None):
    pkgpath = pkg.__path__
    if submodule_names is None:
        submodule_names = dir(pkg)
    for key in submodule_names:
        val = getattr(pkg, key)
        if key.startswith('_'):
            continue
        if type(val) != types.ModuleType:
            continue
        for pfx in system_prefixes:
            if pfx in val.__file__:
                continue
        if '__init__.py' in os.path.basename(val.__file__):
            subpkgpath = ['/'.join([vpath[0], key])]
            add_linked_package(subpkgpath, val)
        add_linked_module('.'.join(vpath[0].split('/')), val)
    
def add_linked_module(vpath, mod):
    modname = mod.__name__.rsplit('.', 1)[1]
    fullname = '.'.join([vpath, modname])
    LINKED_MODULES[fullname] = mod


class LinkedModuleFinder(object):
    def find_module(self, fullname, path=None):
        mod = LINKED_MODULES.get(fullname)
        if mod is not None:
            #print 'found linked module: fullname=%s, path=%s, modpath=%s, mod=%s' % (fullname, path, getattr(mod, '__path__', None), mod)
            return self
        return None
    def load_module(self, fullname):
        try:
            return LINKED_MODULES[fullname]
        except:
            raise ImportError('LinkedModule could not load %s' % (fullname))


sys.meta_path.append(LinkedModuleFinder())
