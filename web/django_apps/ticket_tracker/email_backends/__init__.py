from base import BaseEmailBackend
from pygmail import PyGMailBackend

BACKENDS = {'gmail':PyGMailBackend}

def build_backend(name, **kwargs):
    cls = BACKENDS[name]
    return cls(**kwargs)
