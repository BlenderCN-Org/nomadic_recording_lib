import code
import os.path
import sys
import socket
import select

if __name__ == '__main__':
    dirname = os.path.dirname(__file__)
    if dirname == '':
        dirname = os.getcwd()
        sys.path.append(dirname)
    i = sys.path.index(dirname)
    sys.path[i] = os.path.split(os.path.split(sys.path[i])[0])[0]
    print sys.path[i]

from Bases import BaseObject, BaseThread
from comm.BaseIO import BaseIO

PORT = 54321

class RemoteClient(BaseIO):
    pass
    
class RemoteConsole(code.InteractiveConsole):
    def __init__(self, **kwargs):
        code.InteractiveConsole.__init__(self)
        self.host_addr = kwargs.get('host_addr', '127.0.0.1')
        self.host_port = kwargs.get('host_port', PORT)
        self._sock = None
    @property
    def sock(self):
        s = self._sock
        if s is None:
            s = self.build_socket()
            self._sock = s
        return s
    def build_socket(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #s.settimeout(4.)
        s.connect((self.host_addr, self.host_port))
        print 'socket built: ', s
        return s
    def close_socket(self):
        s = self._sock
        if s is not None:
            s.close()
            print 'socket closed: ', s
            self._sock = None
    def runsource(self, source, filename="<input>", symbol="single"):
        #s = self.sock
        source = '%s\n' % (source)
        print 'sending source: ', ' '.join([hex(ord(c)) for c in source])
        #s.send(source)
        print 'waiting...'
        resp = self.send_and_wait(source)
        print 'resp: ', resp
        if resp is not None:
            self.write(resp)
        self.close_socket()
    def send_and_wait(self, to_send):
        data = None
        s = self.sock
        while s is not None:
            s = self._sock
            if s is None:
                continue
            if to_send is not None:
                sargs = [[], [s], []]
            else:
                sargs = [[s], [], []]
            r, w, e = select.select(*sargs)
            if to_send is not None:
                if s in w:
                    print 'sending thru socket: ', to_send, s
                    s.sendall(to_send)
                    print 'data sent'
                    to_send = None
                continue
            if s not in r:
                continue
            print 'socket ready to receive...', s
            data = ''
            newdata = s.recv(4096)
            data += newdata
            print 'data: ', data
            while len(newdata):
                newdata = s.recv(4096)
                data += newdata
                print 'data: ', data
            #self.handle_response(data)
            self.close_socket()
            break
        return data
    
if __name__ == '__main__':
    console = RemoteConsole()
    #if readfunc is not None:
    #    console.raw_input = readfunc
    #else:
    try:
        import readline
    except ImportError:
        pass
    console.interact()
