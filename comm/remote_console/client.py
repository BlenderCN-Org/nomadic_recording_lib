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
        s.settimeout(4.)
        s.connect((self.host_addr, self.host_port))
        return s
    def close_socket(self):
        s = self._sock
        if s is not None:
            s.close()
            self._sock = None
    def runsource(self, source, filename="<input>", symbol="single"):
        s = self.sock
        print 'sending source: ', source
        s.send(source)
        print 'waiting...'
        resp = self.wait_for_response()
        print 'resp: ', resp
        if resp is not None:
            self.write(resp)
        self.close_socket()
    def wait_for_response(self):
        data = None
        while self.sock is not None:
            s = self.sock
            r, w, e = select.select([s], [], [], .1)
            if s not in r:
                continue
            data = ''
            newdata = s.recv(4096)
            data += newdata
            while len(newdata):
                newdata = s.recv(4096)
                data += newdata
            #self.handle_response(data)
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
