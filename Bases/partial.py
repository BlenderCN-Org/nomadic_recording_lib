import functools

class Partial(object):
    def __init__(self, cb, *args, **kwargs):
        obj = cb.im_self
        self.id = id(obj)
        self.obj_name = obj.__class__.__name__
        self.func_name = cb.im_func.func_name
        self._partial = functools.partial(cb, *args, **kwargs)
    @property
    def cb(self):
        return self._partial.func
    @property
    def args(self):
        return self._partial.args
    @property
    def kwargs(self):
        return self._partial.keywords
    def __call__(self):
        self._partial()
    def __str__(self):
        return '%s(%s), %s' % (self.obj_name, self.id, self.func_name)
    def __repr__(self):
        return 'Partial object %s: %s' % (id(self), str(self))
