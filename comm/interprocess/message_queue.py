import multiprocessing

from ..BaseIO import BaseIO

class _ClientPointer(object):
    pass
    
class QueueServer(BaseIO):
    _ChildGroups = {'clients':dict(child_class=_ClientPointer)}
    def __init__(self, **kwargs):
        super(QueueServer, self).__init__(**kwargs)
        self.hostaddr = kwargs.get('hostaddr', '')
        self.hostport = int(kwargs.get('hostport', 50000))
        self.authkey = kwargs.get('authkey', '1234567890')
        self.clients.bind(update=self.on_clients_Childgroup_update)
    def on_clients_Childgroup_update(self, **kwargs):
        pass
        
class QueueClient(BaseIO):
    def __init__(self, **kwargs):
        super(QueueClient, self).__init__(**kwargs)
        
