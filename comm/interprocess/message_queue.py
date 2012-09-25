import os.path
import sys
import socket
import SocketServer


if __name__ == '__main__':
    dirname = os.path.dirname(__file__)
    if dirname == '':
        dirname = os.getcwd()
        sys.path.append(dirname)
    i = sys.path.index(dirname)
    sys.path[i] = os.path.split(sys.path[i])[0]
    sys.path[i] = os.path.split(sys.path[i])[0]
    print sys.path[i]

from Bases import BaseObject, BaseThread, Scheduler, setID
from comm.BaseIO import BaseIO

DEFAULT_PORT = 51515
BUFFER_SIZE = 4096

class QueueMessage(object):
    _message_keys = ['client_id', 'client_address', 'timestamp', 
                     'message_id', 'message_type', 'data']
    _datetime_fmt_str = '%Y-%m-%d %H:%M:%S.%f'
    def __init__(self, **kwargs):
        raw_data = kwargs.get('raw_data')
        if raw_data is not None:
            d = self.deserialize(raw_data)
            d.update(kwargs)
        else:
            d = kwargs
        self.load_data(d)
    def load_data(self, data):
        for key in self._message_keys:
            val = kwargs.get(key)
            setattr(self, key, val)
    def serialize(self):
        keys = self._message_keys
        d = {}
        for key in keys:
            val = getattr(self, key)
            if isinstance(val, datetime.datetime):
                val = val.strftime(val, self._datetime_fmt_str)
            d[key] = val
        #d = dict(zip(keys, [getattr(self, key) for key in keys]))
        return json.dumps(d)
    def deserialize(self, data):
        d = json.loads(data)
        ts = d.get('timestamp')
        if ts is not None:
            dt = datetime.datetime.strptime(ts, self._datetime_fmt_str)
            d['timestamp'] = dt
        return d
    
    
class MessageHandler(BaseObject):
    def __init__(self, **kwargs):
        super(MessageHandler, self).__init__(**kwargs)
        self.register_signal('new_message')
        self.message_class = kwargs.get('message_class', QueueMessage)
        self.queue_time_method = kwargs.get('queue_time_method', 'datetime_utc')
        self.message_queue = Scheduler(time_method=self.queue_time_method, 
                                       callback=self.dispatch_message)
        self.message_queue.start()
    def incoming_data(self, **kwargs):
        data = kwargs.get('data')
        client = kwargs.get('client')
        mq = self.message_queue
        msg = self.message_class(raw_data=data, 
                                 client_address=client)
        ts = msg.timestamp
        if ts is None:
            ts = mq.now()
        mq.add_item(ts, msg)
    
    def dispatch_message(self, msg, ts):
        self.emit('new_message', message=msg, timestamp=ts)
    
class QueueClient(BaseObject):
    def __init__(self, **kwargs):
        super(QueueClient, self).__init__(**kwargs)
        self.id = kwargs.get('id')
        self.hostaddr = kwargs.get('hostaddr')
        self.hostport = kwargs.get('hostport')
        self.queue_parent = kwargs.get('queue_parent')
    def send_message(self, **kwargs):
        pass
        
class QueueBase(BaseIO):
    _ChildGroups = {'clients':dict(child_class=QueueClient, ignore_index=True)}
    def __init__(self, **kwargs):
        super(QueueBase, self).__init__(**kwargs)
        self.register_signal('new_message')
        self.id = setID(kwargs.get('id'))
        self.hostaddr = kwargs.get('hostaddr', '127.0.0.1')
        self.hostport = int(kwargs.get('hostport', DEFAULT_PORT))
        self.message_handler = MessageHandler()
        self.message_handler.bind(new_message=self.on_handler_new_message)
    def add_client(self, **kwargs):
        kwargs['queue_parent'] = self
        c = self.clients.add_child(**kwargs)
        return c
    def del_client(self, **kwargs):
        c_id = kwargs.get('id')
        client = kwargs.get('client')
        if client is None:
            client = self.clients.get(c_id)
        if client is None:
            return
        self.clients.remove_child(client)
    def on_handler_new_message(self, **kwargs):
        self.emit('new_message', **kwargs)
        msg = kwargs.get('message')
        c_id = msg.client_id
        client = self.clients.get(c_id)
        if client is not None:
            client.send_message(message_type='message_received', data=msg.message_id)
        
        
class QueueServer(QueueBase):
    def __init__(self, **kwargs):
        super(QueueServer, self).__init__(**kwargs)
        self.serve_thread = None
        
    def do_connect(self):
        self.do_disconnect(blocking=True)
        t = self.serve_thread = self.build_server()
        t.start()
        self.connected = True
    def do_disconnect(self, **kwargs):
        t = self.serve_thread
        if t is not None:
            t.stop(blocking=True)
            self.serve_thread = None
        self.connected = False
    def build_server(self):
        t = ServeThread(hostaddr=self.hostaddr, 
                        hostport=self.hostport, 
                        message_handler=self.message_handler)
        return t
    
    
class QueueClient(QueueBase):
    def __init__(self, **kwargs):
        super(QueueClient, self).__init__(**kwargs)
        
        
class _Server(SocketServer.TCPServer):
    pass
    #def __init__(self, *args):
    #    SocketServer.TCPServer.__init__(self, *args)
class _RequestHandler(SocketServer.BaseRequestHandler):
    def handle(self):
        data = self.request.recv(BUFFER_SIZE)
        client = self.client_address
        mh = self.server.message_handler
        mh.incoming_data(data=data, client=client)
        
class ServeThread(BaseThread):
    def __init__(self, **kwargs):
        kwargs['disable_threaded_call_waits'] = True
        super(ServeThread, self).__init__(**kwargs)
        self.hostaddr = kwargs.get('hostaddr')
        self.hostport = kwargs.get('hostport')
        self.message_handler = kwargs.get('message_handler')
        self._server = None
    def build_server(self):
        host = (self.hostaddr, self.hostport)
        s = _Server(host, _RequestHandler)
        s.message_handler = self.message_handler
        return s
    def _thread_loop_iteration(self):
        if not self._running:
            return
        if self._server is not None:
            return
        s = self._server = self.build_server()
        s.serve_forever()
    def stop(self, **kwargs):
        s = self._server
        if s is not None:
            s.shutdown()
        super(ServerThread, self).stop(**kwargs)

