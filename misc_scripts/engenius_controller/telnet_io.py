import telnetlib

from cli_messages import MessageIO

class TelnetIO(object):
    def __init__(self, **kwargs):
        self.host = kwargs.get('host')
        self.connected = False
        self.connection = None
        self.message_io = MessageIO(tx_fn=self.send, rx_fn=self.read_until)
    def connect(self):
        self.connection = telnetlib.Telnet(self.host)
        self.connected = True
    def disconnect(self):
        if not self.connected:
            return
        self.connection.close()
        self.connection = None
        self.connected = False
    def send(self, msg):
        if not self.connected:
            self.connect()
        self.connection.write(msg)
    def read_until(self, s):
        return self.connection.read_until(s)
