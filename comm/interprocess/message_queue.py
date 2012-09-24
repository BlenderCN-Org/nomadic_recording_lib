import os.path
import sys
from multiprocessing.managers import BaseManager as _mpBaseManager
import Queue

if __name__ == '__main__':
    dirname = os.path.dirname(__file__)
    if dirname == '':
        dirname = os.getcwd()
        sys.path.append(dirname)
    i = sys.path.index(dirname)
    sys.path[i] = os.path.split(sys.path[i])[0]
    sys.path[i] = os.path.split(sys.path[i])[0]
    print sys.path[i]

from Bases import BaseObject, setID
from comm.BaseIO import BaseIO

DEFAULT_PORT = 51515

class _ClientPointer(BaseObject):
    _Properties = {'connected':dict(default=False)}
    def __init__(self, **kwargs):
        super(_ClientPointer, self).__init__(**kwargs)
        self.id = kwargs.get('id')
        self._queues = {'in':None, 'out':None}
        self.q_server = kwargs.get('queue_server')
        if self.q_server.connected:
            self.connect()
        self.q_server.bind(connected=self.on_queue_server_state)
    def unlink(self):
        self.q_server.unbind(self)
        super(_ClientPointer, self).unlink()
    @property
    def queues(self):
        q = self._queues
        if None in q:
            q = self._build_queues()
            self._queues.update(q)
        return q
    def _build_queues(self):
        return dict(zip(['in', 'out'], [Queue.Queue(), Queue.Queue()]))
    def connect(self):
        pass
    def disconnect(self):
        pass
    def on_queue_server_state(self, **kwargs):
        state = kwargs.get('value')
        if state:
            self.connect()
        else:
            self.disconnect()
    
class QueueBase(BaseIO):
    def __init__(self, **kwargs):
        super(QueueBase, self).__init__(**kwargs)
        self._manager = None
        self.hostaddr = kwargs.get('hostaddr')
        self.hostport = int(kwargs.get('hostport', DEFAULT_PORT))
        self.authkey = kwargs.get('authkey', '1234567890')
    def _build_manager_cls(self, **kwargs):
        class _QueueManager(_mpBaseManager):
            pass
        registry = kwargs.get('registry', {})
        default_reg = {'client_request_queues':None, 
                       'client_adding_self':None}
        default_reg.update(registry)
        for key, val in default_reg.iteritems():
            if val is None:
                val = getattr(self, key, None)
            args = [key]
            if val is not None:
                args.append(val)
            _QueueManager.register(*args)
        return _QueueManager
    def _build_manager(self, **kwargs):
        cls = self._build_manager_cls(**kwargs)
        addr = (self.hostaddr, self.hostport)
        m = cls(address=addr, authkey=self.authkey)
        return m
class QueueServer(QueueBase):
    _ChildGroups = {'clients':dict(child_class=_ClientPointer, ignore_index=True)}
    def __init__(self, **kwargs):
        kwargs.setdefault('hostaddr', '')
        super(QueueServer, self).__init__(**kwargs)
        self.clients.bind(update=self.on_clients_Childgroup_update)
    def do_connect(self, **kwargs):
        if self.connected:
            return
        if self._manager is not None:
            self.do_disconnect(blocking=True)
        m = self._build_manager()
        self._manager = m
        m.start()
        self.connected = True
    def do_disconnect(self, **kwargs):
        m = self._manager
        if m is not None:
            m.shutdown()
            self._manager = None
        self.connected = False
    
    def add_client(self, **kwargs):
        kwargs = kwargs.copy()
        kwargs['queue_server'] = self
        c = self.clients.add_child(**kwargs)
        return c
    def remove_client(self, **kwargs):
        client = kwargs.get('client')
        c_id = kwargs.get('id')
        if client is None:
            client = self.clients.get(c_id)
        if client is None:
            return
        self.clients.del_child(client)
    def client_adding_self(self, client_id):
        if client_id in self.clients:
            return False
        c = self.add_client(id=client_id)
        return True
    def client_request_queues(self, client_id, key):
        c = self.clients.get(client_id)
        if c is None:
            return False
        return c.queues.get(key)
    def on_clients_Childgroup_update(self, **kwargs):
        print 'server client update: ', kwargs
        

class QueueClient(QueueBase):
    def __init__(self, **kwargs):
        kwargs.setdefault('hostaddr', '127.0.0.1')
        super(QueueClient, self).__init__(**kwargs)
        self._queues = {'in':None, 'out':None}
        self.id = setID(kwargs.get('id'))
    @property
    def queues(self):
        return self._queues
    def get_queues(self):
        m = self._manager
        q = self._queues
        noqueue = ({'in':None, 'out':None})
        if m is None:
            q.update(noqueue)
            return
        _qdict = {}
        for key in ['in', 'out']:
            _q = m.client_request_queues(self.id, key)
            if _q is not False:
                _qdict[key] = _q
        if not len(_qdict):
            q.update(noqueue)
            return
        q.update(_qdict)
        print 'client %s queues: %r' % (self.id, q)
        print q['in'].__dict__
        
    def do_connect(self, **kwargs):
        if self.connected:
            return
        if self._manager is not None:
            self.do_disconnect(blocking=True)
        m = self._build_manager()
        self._manager = m
        m.connect()
        m.client_adding_self(self.id)
        self.get_queues()
        self.connected = True
    def do_disconnect(self, **kwargs):
        self._close_manager()
        self._manager = None
        self.connected = False
    def _close_manager(self):
        ## TODO: figure out how to close it?
        pass

def test_server():
    serv = QueueServer()
    print 'serv: ', serv
    serv.do_connect()
    print 'serv connected'
    return serv
def test_client():
    c = QueueClient()
    c.do_connect()
    return c
if __name__ == '__main__':
    import time
    serv = test_server()
    c = test_client()
    running = True
    while running:
        try:
            time.sleep(.5)
        except KeyboardInterrupt:
            running = False
    c.do_disconnect()
    serv.do_disconnect()
