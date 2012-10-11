import os.path
import sys
import time
import socket
import SocketServer
import collections
import datetime
import json
import threading
import traceback
from Crypto.Cipher import AES


if __name__ == '__main__':
    dirname = os.path.dirname(__file__)
    if dirname == '':
        dirname = os.getcwd()
        sys.path.append(dirname)
    i = sys.path.index(dirname)
    sys.path[i] = os.path.split(sys.path[i])[0]
    sys.path[i] = os.path.split(sys.path[i])[0]

from Bases import BaseObject, BaseThread, Scheduler, setID
from comm.BaseIO import BaseIO

DEFAULT_PORT = 51515
BUFFER_SIZE = 4096
SEND_RETIES = 20
SEND_RETRY_TIMEOUT = 10.
POLL_INTERVAL = datetime.timedelta(minutes=1)

DATETIME_FMT_STR = '%Y-%m-%d %H:%M:%S.%f'
def datetime_to_str(dt):
    return dt.strftime(DATETIME_FMT_STR)
def str_to_datetime(s):
    return datetime.datetime.strptime(s, DATETIME_FMT_STR)

class QueueMessage(object):
    _message_keys = ['sender_id', 'sender_address', 'recipient_id', 
                     'recipient_address', 'timestamp', 
                     'message_id', 'message_type', 'data']
    def __init__(self, **kwargs):
        self.message_handler = kwargs.get('message_handler')
        raw_data = kwargs.get('raw_data')
        if raw_data is not None:
            d = self.deserialize(raw_data)
            d.update(kwargs)
        else:
            d = kwargs
        self.load_data(d)
        if self.timestamp is None:
            self.timestamp = self.message_handler.message_queue.now()
        if self.message_id is None:
            self.message_id = (self.recipient_id, datetime_to_str(self.timestamp))
        for key in ['recipient_address', 'sender_address', 'message_id']:
            val = getattr(self, key)
            if type(val) == list:
                setattr(self, key, tuple(val))
    def load_data(self, data):
        for key in self._message_keys:
            val = data.get(key)
            setattr(self, key, val)
    def serialize(self):
        keys = self._message_keys
        d = {}
        for key in keys:
            val = getattr(self, key)
            if isinstance(val, datetime.datetime):
                val = datetime_to_str(val)
            d[key] = val
        return json.dumps(d)
    def deserialize(self, data):
        d = json.loads(data)
        ts = d.get('timestamp')
        if ts is not None:
            dt = str_to_datetime(ts)
            d['timestamp'] = dt
        return d
    def __repr__(self):
        return '<%s object (%s)>' % (self.__class__.__name__, self)
    def __str__(self):
        return str(dict(zip(self._message_keys, [getattr(self, key, None) for key in self._message_keys])))
    
class AESEncryptedMessage(QueueMessage):
    cipher = None
    def __init__(self, **kwargs):
        if self.cipher is None:
            mh = kwargs.get('message_handler')
            key = mh.queue_parent.message_key
            if key is None:
                key = ''.join([chr(i) for i in range(32)])
            self.set_message_key(key)
        super(AESEncryptedMessage, self).__init__(**kwargs)
    @staticmethod
    def pad_zeros(s, size=16):
        if len(s) == size:
            return s
        padlen = size - len(s)
        s += '\0' * padlen
        return s
    @classmethod
    def set_message_key(cls, key):
        sizes = [32, 24, 16]
        if len(key) in sizes:
            padded = key
        if len(key) > max(sizes):
            size = max(sizes)
            padded = key[size:]
        else:
            for size in sizes:
                if len(key) > size:
                    continue
                padded = cls.pad_zeros(key, size)
                break
        cls.cipher = AES.new(padded)
    def serialize(self):
        msg = super(AESEncryptedMessage, self).serialize()
        size = len(msg)
        while size % 16 != 0:
            size += 1
        padded = self.pad_zeros(msg, size)
        c = self.cipher
        if c is None:
            return
        s = c.encrypt(padded)
        return s
        
    def deserialize(self, data):
        c = self.cipher
        if c is None:
            return
        msg = c.decrypt(data)
        msg = msg.strip('\0')
        return super(AESEncryptedMessage, self).deserialize(msg)
    
MESSAGE_CLASSES = {'Message':QueueMessage, 'AES':AESEncryptedMessage}

class MessageHandler(BaseObject):
    def __init__(self, **kwargs):
        super(MessageHandler, self).__init__(**kwargs)
        self.register_signal('new_message')
        self.queue_parent = kwargs.get('queue_parent')
        mcls = kwargs.get('message_class', getattr(self.queue_parent, 'message_class', 'Message'))
        self.message_class = MESSAGE_CLASSES.get(mcls)
        self.queue_time_method = kwargs.get('queue_time_method', 'datetime_utc')
        self.message_queue = Scheduler(time_method=self.queue_time_method, 
                                       callback=self.dispatch_message)
        self.message_queue.start()
    def unlink(self):
        self.message_queue.stop(blocking=True)
        q = self.message_queue
        super(MessageHandler, self).unlink()
    def create_message(self, **kwargs):
        cls = self.message_class
        kwargs['message_handler'] = self
        return cls(**kwargs)
    def incoming_data(self, **kwargs):
        data = kwargs.get('data')
        client = kwargs.get('client')
        mq = self.message_queue
        try:
            msg = self.create_message(raw_data=data)
        except:
            self.LOG.warning('message parse error: client = (%s), data = (%s)' % (client, data))
            return
        #self.LOG.info('incoming message: %s' % (msg))
        if msg.recipient_address is None:
            msg.recipient_address = client
        ts = msg.timestamp
        if ts is None:
            ts = mq.now()
        mq.add_item(ts, msg)
    
    def dispatch_message(self, msg, ts):
        self.emit('new_message', message=msg, timestamp=ts)
    
class Client(BaseObject):
    _Properties = {'hostaddr':dict(ignore_type=True), 
                   'hostport':dict(ignore_type=True)}
    def __init__(self, **kwargs):
        super(Client, self).__init__(**kwargs)
        self.register_signal('new_message')
        self.id = kwargs.get('id')
        self.hostaddr = kwargs.get('hostaddr')
        self.hostport = kwargs.get('hostport', DEFAULT_PORT)
        self.is_local_client = kwargs.get('is_local_client', False)
        self.queue_parent = kwargs.get('queue_parent')
        self.pending_messages = {}
    def send_message(self, **kwargs):
        kwargs = kwargs.copy()
        self._update_message_kwargs(kwargs)
        msg = self.queue_parent._do_send_message(**kwargs)
        return msg
    def _on_message_built(self, msg):
        if msg.recipient_id != self.id:
            return
        if msg.message_type == 'message_receipt':
            return
        ##d = self.pending_messages.get(msg.recipient_id)
        ##if d is None:
        ##    d = {}
        ##    self.pending_messages[msg.recipient_id] = d
        ##d[msg.message_id] = {'message':msg, 'attempts':1}
    def _update_message_kwargs(self, kwargs):
        d = {'recipient_id':self.id, 
             'recipient_address':(self.hostaddr, self.hostport)}
        kwargs.update(d)
    def _send_message_receipt(self, msg, **kwargs):
        return
        kwargs = kwargs.copy()
        msg_data = dict(message_type='message_receipt', 
                        data=msg.message_id, 
                        message_id=None, 
                        timestamp=None, 
                        client_id=msg.sender_id)
        #kwargs.update(msg_data)
        self.queue_parent.send_message(**msg_data)
    def update_hostdata(self, data):
        for attr in ['hostaddr', 'hostport']:
            if attr not in data:
                continue
            val = data[attr]
            if getattr(self, attr) == val:
                continue
            setattr(self, attr, val)
    def handle_message(self, **kwargs):
        msg = kwargs.get('message')
        if msg.message_type == 'message_receipt':
            d = self.pending_messages.get(msg.sender_id)
            if d is None:
                return
            msgid = msg.data
            if type(msgid) == list:
                msgid = tuple(msgid)
            if msgid not in d:
                return
            del d[msgid]
        elif msg.message_type == 'hostdata_update':
            if not isinstance(msg.data, dict):
                return
            self.update_hostdata(msg.data)
            return
        self._send_message_receipt(msg, **kwargs)
        self.update_hostdata(dict(zip(['hostaddr', 'hostport'], msg.sender_address)))
        kwargs['obj'] = self
        self.emit('new_message', **kwargs)
    def __repr__(self):
        return '<%s>' % (self)
    def __str__(self):
        return 'Client: %s, hostdata=(%s, %s)' % (self.id, self.hostaddr, self.hostport)
        
class QueueBase(BaseIO):
    _ChildGroups = {'clients':dict(child_class=Client, ignore_index=True)}
    def __init__(self, **kwargs):
        super(QueueBase, self).__init__(**kwargs)
        self.register_signal('new_message')
        self.id = setID(kwargs.get('id'))
        self.message_key = kwargs.get('message_key')
        hostaddr = kwargs.get('hostaddr', '127.0.0.1')
        hostport = int(kwargs.get('hostport', DEFAULT_PORT))
        self.message_class = kwargs.get('message_class', 'Message')
        self.message_handler = MessageHandler(queue_parent=self)
        self.message_handler.bind(new_message=self.on_handler_new_message)
        self.local_client = self.add_client(hostaddr=hostaddr, 
                                            hostport=hostport, 
                                            id=self.id, 
                                            is_local_client=True)
        self.local_client.bind(property_changed=self.on_local_client_property_changed)
    @property
    def hostaddr(self):
        return self.local_client.hostaddr
    @hostaddr.setter
    def hostaddr(self, value):
        self.local_client.hostaddr = value
    @property
    def hostport(self):
        return self.local_client.hostport
    @hostport.setter
    def hostport(self, value):
        self.local_client.hostport = value
    def unlink(self):
        self.message_handler.unlink()
        #self.clients.clear()
        super(QueueBase, self).unlink()
    def add_client(self, **kwargs):
        kwargs['queue_parent'] = self
        c = self.clients.add_child(**kwargs)
        if not c.is_local_client:
            self.send_hostdata_to_clients(clients=c)
        return c
    def del_client(self, **kwargs):
        c_id = kwargs.get('id')
        client = kwargs.get('client')
        if client is None:
            client = self.clients.get(c_id)
        if client is None:
            return
        self.clients.del_child(client)
    def on_handler_new_message(self, **kwargs):
        msg = kwargs.get('message')
        if msg == 'POLL':
            self.on_poll_interval()
            return
        c_id = msg.sender_id
        client = self.clients.get(c_id)
        #self.LOG.info('handling message: %s, client=%s' % (msg, client))
        if client is not None:
            client.handle_message(**kwargs)
        else:
            self.emit('new_message', **kwargs)
    def _update_message_kwargs(self, kwargs):
        d = {'sender_id':self.id, 'sender_address':(self.hostaddr, self.hostport)}
        kwargs.update(d)
    def send_message(self, **kwargs):
        kwargs = kwargs.copy()
        client = kwargs.get('client')
        c_id = kwargs.get('client_id')
        if not isinstance(client, Client):
            if client is not None:
                client = self.clients.get(client)
            if client is None:
                client = self.clients.get(c_id)
        if isinstance(client, Client):
            client._update_message_kwargs(kwargs)
        msg = self._do_send_message(**kwargs)
        return msg
    def _do_send_message(self, **kwargs):
        msg = self.create_message(**kwargs)
        client = self.clients.get(msg.recipient_id)
        if client is not None:
            client._on_message_built(msg)
        #self.LOG.info('sending message: %s' % (msg))
        s = msg.serialize()
        h = kwargs.get('handler')
        sock = None
        try:
            if h is not None:
                sock = h.request
            else:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect(msg.recipient_address)
            sock.sendall(s)
            if h is None:
                sock.close()
        except:
            self.LOG.warning(traceback.format_exc())
        return msg
        
    def create_message(self, **kwargs):
        self._update_message_kwargs(kwargs)
        msg = self.message_handler.create_message(**kwargs)
        return msg
        
    def on_poll_interval(self):
        self.send_hostdata_to_clients()
        mq = self.message_handler.message_queue
        nextpoll = mq.now() + POLL_INTERVAL
        mq.add_item(nextpoll, 'POLL')
        
    def send_hostdata_to_clients(self, **kwargs):
        keys = kwargs.get('keys')
        clients = kwargs.get('clients')
        if not keys:
            keys = ['hostaddr', 'hostport']
        if clients is not None and type(clients) not in [list, tuple, set]:
            clients = [clients]
        elif clients is None:
            clients = self.clients
        d = dict(zip(keys, [getattr(self, key) for key in keys]))
        for c in self.clients.itervalues():
            if c.is_local_client:
                continue
            c.send_message(message_type='hostdata_update', data=d)
            
    def on_local_client_property_changed(self, **kwargs):
        prop = kwargs.get('Property')
        value = kwargs.get('value')
        if prop.name in ['hostaddr', 'hostport']:
            self.send_hostdata_to_clients(keys=[prop.name])
        
class QueueServer(QueueBase):
    def __init__(self, **kwargs):
        super(QueueServer, self).__init__(**kwargs)
        self.serve_thread = None
        
    def do_connect(self):
        self.do_disconnect(blocking=True)
        t = self.serve_thread = self.build_server()
        t.bind(hostport=self.on_server_hostport_changed)
        t.start()
        self.connected = True
        self.on_poll_interval()
    def do_disconnect(self, **kwargs):
        t = self.serve_thread
        if t is not None:
            t.unbind(self)
            t.stop(blocking=True)
            self.serve_thread = None
        self.connected = False
    def shutdown(self):
        self.do_disconnect(blocking=True)
        self.unlink()
    def build_server(self):
        t = ServeThread(hostaddr='', 
                        hostport=self.hostport, 
                        message_handler=self.message_handler)
        return t
    def on_server_hostport_changed(self, **kwargs):
        value = kwargs.get('value')
        if value != self.hostport:
            self.hostport = value
    
    
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
        mh.incoming_data(data=data, client=client, handler=self)
        
class ServeThread(BaseThread):
    _Properties = {'hostaddr':dict(ignore_type=True), 
                   'hostport':dict(ignore_type=True)}
    def __init__(self, **kwargs):
        super(ServeThread, self).__init__(**kwargs)
        self.hostaddr = kwargs.get('hostaddr')
        self.hostport = kwargs.get('hostport')
        self.message_handler = kwargs.get('message_handler')
        self._server = None
    def build_server(self):
        addr = self.hostaddr
        port = int(self.hostport)
        count = 0
        maxtries = 100
        while count < maxtries:
            try:
                s = _Server((addr, port), _RequestHandler)
                break
            except socket.error:
                port += 1
            count += 1
        self.hostport = port
        s.message_handler = self.message_handler
        return s
    def run(self):
        self._running = True
        s = self._server = self.build_server()
        self.message_handler.LOG.info('%r STARTING' % (self))
        s.serve_forever()
        self._running = False
        self._stopped = True
        self.message_handler.LOG.info('%r STOPPED' % (self))
    def stop(self, **kwargs):
        s = self._server
        if s is not None:
            s.shutdown()
        self._stopped.wait()

if __name__ == '__main__':
    import argparse
    class TestObj(object):
        def on_message(self, **kwargs):
            print 'message received: ', kwargs
    p = argparse.ArgumentParser()
    p.add_argument('--host', dest='host')
    p.add_argument('--client', dest='client')
    args, remaining = p.parse_known_args()
    o = vars(args)
    testobj = TestObj()
    serv = QueueServer(id=o['host'], hostaddr=o['host'])
    serv.bind(new_message=testobj.on_message)
    serv.local_client.bind(new_message=testobj.on_message)
    serv.do_connect()
    print 'server connected'
    c = serv.add_client(id=o['client'], hostaddr=o['client'])
    c.bind(new_message=testobj.on_message)
    time.sleep(1.)
    print 'sending message'
    msg = c.send_message(data='hi')
    print 'message sent', msg
    while True:
        try:
            time.sleep(.5)
        except KeyboardInterrupt:
            print 'disconnecting'
            serv.shutdown()
            break
    print 'disconnected'
    
