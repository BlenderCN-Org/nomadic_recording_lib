import socket
import uuid

class SystemData(object):
    def __init__(self):
        self.name = socket.gethostname()
        self.id = uuid.uuid4().urn
        self.appname = 'Lighting Control'
        self.address = None
        self.hostname = self.name + '.local'
