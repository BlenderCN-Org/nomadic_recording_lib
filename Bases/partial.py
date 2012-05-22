import threading
import functools
import weakref

class Partial(object):
    #__slots__ = ('call_time', 'id', 'obj_name', 'func_name', '_partial')
    def __init__(self, cb, *args, **kwargs):
        self.call_lock = threading.Lock()
        self.call_count = 0
        self.call_time = kwargs.get('_Partial_call_time_')
        obj = cb.im_self
        self.obj_name = obj.__class__.__name__
        self.func_name = cb.im_func.func_name
        #self.id = '_'.join([id(obj), self.func_name])
        self.id = id(cb)
        self._partial = self._build_partial(cb, *args, **kwargs)
    def __hash__(self):
        return self.id
    def _build_partial(self, cb, *args, **kwargs):
        return functools.partial(cb, *args, **kwargs)
    @property
    def cb(self):
        return self._partial.func
    @property
    def args(self):
        return self._partial.args
    @property
    def kwargs(self):
        return self._partial.keywords
    def __call__(self, *args, **kwargs):
        with self.call_lock:
            self.call_count += 1
            self._partial()
    def __str__(self):
        #s = '%s(%s), %s' % (self.obj_name, self.id, self.func_name)
        s = repr(self._partial.func)
        t = self.call_time
        if t is not None:
            s = '%s (%s)' % (s, t)
        return s
    def __repr__(self):
        return '<Partial object %s: %s>' % (id(self), str(self))
        
class WeakPartial(Partial):
    def __init__(self, cb, dead_cb, *args, **kwargs):
        self.dead_cb = dead_cb
        super(WeakPartial, self).__init__(cb, *args, **kwargs)
    @property
    def is_dead(self):
        return self._partial.is_dead
    def _build_partial(self, cb, *args, **kwargs):
        return WeakPartialPartial(cb, self._on_partial_dead, *args, **kwargs)
    def _on_partial_dead(self, p):
        print self, 'obj unref'
        cb = self.dead_cb
        if cb is None:
            return
        cb(self)
    
class WeakPartialPartial(object):
    def __init__(self, cb, dead_cb, *args, **kwargs):
        self.dead_cb = dead_cb
        self._is_dead = False
        obj = getattr(cb, 'im_self', None)
        if obj is not None:
            self.obj = weakref.ref(obj, self._on_obj_unref)
        else:
            self.obj = None
        self.func_name = cb.im_func.func_name
        self.args = tuple([a for a in args])
        self.keywords = kwargs.copy()
    @property
    def is_dead(self):
        isdead = self._is_dead
        if isdead:
            return isdead
        if self.obj() is None:
            isdead = True
        if isdead:
            self.is_dead = isdead
        return isdead
    @is_dead.setter
    def is_dead(self, value):
        if value == self._is_dead:
            return
        self._is_dead = value
        if value:
            self.dead_cb(self)
    @property
    def func(self):
        if self.is_dead:
            return None
        return getattr(self.obj(), self.func_name)
    def _on_obj_unref(self, ref):
        self.is_dead = True
    def _on_cb_unref(self, ref):
        self.is_dead = True
    def __call__(self, *args, **kwargs):
        if not len(args):
            args = self.args
        if not len(kwargs):
            kwargs = self.keywords
        if self.is_dead:
            return
        #cb = self.callback()
        return self.func(*args, **kwargs)
