import functools
import weakref

class Partial(object):
    __slots__ = ('call_time', 'id', 'obj_name', 'func_name', '_partial')
    def __init__(self, cb, *args, **kwargs):
        self.call_time = kwargs.get('_Partial_call_time_')
        obj = cb.im_self
        self.id = id(obj)
        self.obj_name = obj.__class__.__name__
        self.func_name = cb.im_func.func_name
        self._partial = self._build_partial(cb, *args, **kwargs)
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
        self._partial()
    def __str__(self):
        s = '%s(%s), %s' % (self.obj_name, self.id, self.func_name)
        t = self.call_time
        if t is not None:
            s = '%s (%s)' % (s, t)
        return s
    def __repr__(self):
        return '<Partial object %s: %s>' % (id(self), str(self))
        
class WeakPartial(Partial):
    def _build_partial(self, cb, *args, **kwargs):
        return WeakPartialPartial(cb, self._on_partial_dead, *args, **kwargs)
    def _on_partial_dead(self, p):
        print self, 'obj unref'
    
class WeakPartialPartial(object):
    def __init__(self, cb, dead_cb, *args, **kwargs):
        self.dead_cb = dead_cb
        self.is_dead = False
        obj = getattr(cb, 'im_self', None)
        if obj is not None:
            self.obj = weakref.ref(obj, self._on_obj_unref)
        else:
            self.obj = None
        self.callback = weakref.ref(cb, self._on_cb_unref)
        self.args = tuple([a for a in args])
        self.kwargs = kwargs.copy()
    def _on_obj_unref(self, ref):
        self.is_dead = True
        self.dead_cb(self)
    def _on_cb_unref(self, ref):
        self.is_dead = True
        self.dead_cb(self)
    def __call__(self):
        if self.is_dead:
            return
        obj = self.obj()
        if obj is None:
            return
        cb = self.callback()
        if cb is None:
            return
        return cb(*args, **kwargs)
