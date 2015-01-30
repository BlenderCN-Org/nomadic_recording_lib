import os
from urlparse import urlparse

import pysftp

class BaseOpener(object):
    def __init__(self, uri, **kwargs):
        self.uri = uri
        self.kwargs = kwargs
        self.file_obj = None
    def __enter__(self):
        self.open()
    def __exit__(self, *args):
        self.close()
        self.file_obj = None
    def open(self):
        pass
    def close(self):
        self.file_obj.close()
    def read(self):
        return self.file_obj.read()
        
class FileOpener(BaseOpener):
    def open(self):
        p = os.path.expanduser(self.uri.geturl())
        self.file_obj = open(p, 'r')
        
class SSHFileOpener(BaseOpener):
    def open(self):
        skwargs = {}
        un = self.kwargs.get('username')
        if un is None:
            un = self.uri.username
        if un is not None:
            skwargs['username'] = un
        if self.uri.port is not None:
            skwargs['port'] = self.uri.port
        pw = self.kwargs.get('password')
        if pw is None:
            pw = self.uri.password
        if pw is not None:
            skwargs['password'] = pw
        pk = self.kwargs.get('private_key')
        if pk is not None:
            skwargs['private_key'] = pk
        pf = self.kwargs.get('private_key_pass')
        if pf is not None:
            skwargs['private_key_pass'] = pf
        self.connection = pysftp.Connection(self.uri.hostname, **skwargs)
        self.connection._sftp_connect()
        self.file_obj = self.connection._sftp.open(self.uri.path, 'r')
    def close(self):
        self.file_obj.close()
        self.file_obj = None
        self.connection.close()
        self.connection = None
        
OPENERS = {'file':FileOpener, 'ssh':SSHFileOpener, 'sftp':SSHFileOpener}

def get_opener(filename, **kwargs):
    uri = urlparse(filename)
    scheme = uri.scheme
    if not scheme:
        scheme = 'file'
    cls = OPENERS.get(scheme)
    return cls(uri, **kwargs)
