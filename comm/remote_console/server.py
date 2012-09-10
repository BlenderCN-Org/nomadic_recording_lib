import SocketServer
import code

from Bases import BaseObject, BaseThread
from ..BaseIO import BaseIO

PORT = 54321

class RemoteServer(BaseIO):
    def __init__(self, **kwargs):
        super(RemoteServer, self).__init__(**kwargs)
        self.locals = kwargs.get('locals')
        self.interpreter = Interpreter(locals=self.locals, 
                                       write_cb=self.on_interpreter_write)
        self.serve_thread = None
    def do_connect(self, **kwargs):
        self.do_disconnect()
        t = self.serve_thread = ServerThread(interpreter=self.interpreter)
        t.start()
        self.connected = True
    def do_disconnect(self, **kwargs):
        t = self.serve_thread
        if t is not None:
            t.stop(blocking=True)
            self.serve_thread = None
        self.connected = False
    def on_interpreter_write(self, data):
        t = self.serve_thread
        if t is None:
            return
        s = t._server
        if s is None:
            return
        h = s.current_handler
        if h is None:
            return
        h.wfile.write(data)
        
class Interpreter(code.InteractiveInterpreter):
    def __init__(self, **kwargs):
        _locals = kwargs.get('locals')
        self.write_cb = kwargs.get('write_cb')
        code.InteractiveInterpreter.__init__(self, _locals)
    def write(self, data):
        cb = self.write_cb
        if cb is not None:
            cb(data)
        
class ServerListener(BaseThread):
    def __init__(self, **kwargs):
        super(ServerListener, self).__init__(**kwargs)
    
class RemoteHandler(SocketServer.StreamRequestHandler):
    def handle(self):
        def get_line():
            return self.rfile.readline().strip()
        self.server.current_handler = self
        line = get_line()
        while len(line):
            process_line(line)
            line = get_line()
    def process_line(self, line):
#        cobj = None
#        try:
#            cobj = code.compile_source(line)
#        except SyntaxError:
#            pass
#        if cobj is None:
#            return
#        #try:
#        #    exec cobj in self.server.locals
        self.server.interpreter.run_source(line)
    def finish(self):
        self.server.current_handler = None
        super(RemoteHandler, self).finish()
        
class ServerThread(BaseThread):
    _server_conf_defaults = dict(server_address=('127.0.0.1', PORT), 
                                 RequestHandlerClass=RemoteHandler, 
                                 bind_and_activate=True)
    def __init__(self, **kwargs):
        kwargs['disable_threaded_call_waits'] = True
        super(ServerListener, self).__init__(**kwargs)
        self.server_config = kwargs.get('server_config', {})
        self.interpreter = kwargs.get('interpreter')
        self._server = None
    def build_server_kwargs(self, **kwargs):
        skwargs = self.server_config.copy()
        for key, default in self._server_conf_defaults.iteritems():
            val = kwargs.get(key, skwargs.get(key, default))
            skwargs[key] = val
        return skwargs
    def _thread_loop_iteration(self):
        if not self._running:
            return
        if self._server is not None:
            return
        skwargs = self.build_server_kwargs()
        s = self._server = SocketServer.TCPServer(**skwargs)
        s.interpreter = self.interpreter
        s.current_handler = None
        s.serve_forever()
    def stop(self, **kwargs):
        s = self._server
        if s is not None:
            s.shutdown()
        super(ServerThread, self).stop(**kwargs)
