import subprocess
import os.path
import threading
import uuid
import bisect

from BaseObject import BaseObject
from RepeatTimer import RepeatTimer

def setID(id):
    if id is None:
        id = str(uuid.uuid4()).replace('-', '_')
        #id = id.urn
    return id
    
popen_kwargs = dict(shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, 
                    stderr=subprocess.STDOUT, close_fds=True)
def get_processes(keyfield=None):
    p = subprocess.Popen('ps xa', **popen_kwargs)
    s = p.stdout.read()
    d = {}
    for lindex, line in enumerate(s.splitlines()):
        fields = line.split()
        if lindex == 0:
            keys = fields
            if keyfield and keyfield in fields:
                keyindex = fields.index(keyfield)
            else:
                keyfield = fields[0]
                keyindex = 0
        else:
            pkey = fields[keyindex]
            d[pkey] = {}
            for kindex, key in enumerate(keys):
                d[pkey][key] = fields[kindex]
    p.kill()
    return d
    
def search_for_process(name):
    ps = get_processes('COMMAND')
    for key, val in ps.iteritems():
        cmd = val['COMMAND']
        if '/' in cmd:
            cmd = os.path.basename(cmd)
        if name in cmd:
            return val['PID']
    return False
    
#    p = subprocess.Popen('ps xa', **popen_kwargs)
#    s = p.stdout.read()
#    for line in s.splitlines():
#        fields = line.split()
#        if len(fields) >= 5:
#            pid = fields[0]
#            pcmd = fields[4]
#            if '/' in pcmd:
#                pcmd = os.path.basename(pcmd)
#            if name in pcmd:
#                return pid
#    return False
    
class SyncThread(threading.Thread):
    def __init__(self, **kwargs):
        threading.Thread.__init__(self)
        self.timeout = kwargs.get('timeout', 3.0)
        self.waiting_thread = threading.currentThread()
        self.callback = kwargs.get('callback')
    def run(self):
        print '%s waiting for %s' % (self.name, self.waiting_thread.name)
        self.waiting_thread.join(self.timeout)
        if not self.waiting_thread.isAlive:
            print '%s done waiting for %s' % (self.name, self.waiting_thread.name)
        else:
            print '%s timed out waiting for %s' % (self.name, self.waiting_thread.name)
        self.callback(self)
        
class GenericPoll(BaseObject):
    def __init__(self, **kwargs):
        super(GenericPoll, self).__init__(**kwargs)
        self.interval = kwargs.get('interval', 2.0)
        self.polling = False
        self.interval_call = kwargs.get('interval_call')
        self.timer = None
    def start_poll(self, **kwargs):
        self.stop_poll()
        self.timer = RepeatTimer(self.interval, self.on_interval)
        self.polling = True
        self.timer.start()
    def stop_poll(self, **kwargs):
        if self.polling:
            self.polling = False
            self.timer.cancel()
        self.timer = None
    def on_interval(self):
        if self.interval_call is not None:
            self.interval_call()
    


def parse_csv(filename):
    file = open(filename, 'r')
    d = {}
    for line_num, line in enumerate(file):
        if line_num == 0:
            keys = [col for col in line.strip().split(',')]
            for key in keys:
                d.update({key:[]})
        else:
            items = [float(item.strip('dB')) for item in line.strip().split(',')]
            for i, item in enumerate(items):
                d[keys[i]].append(item)
    file.close()
    return d


class Interpolator(object):
    def __init__(self, **kwargs):
        self.data = {}
        self.x_keys = []
        points = kwargs.get('points')
        if points is not None:
            for point in points:
                self.add_point(*point)
        
    def add_point(self, x, y):
        #x = self.datatype(x)
        #y = self.datatype(y)
        self.data[x] = y
        if x in self.x_keys:
            return
        self.x_keys = sorted(self.data.keys())
        
    def solve_y(self, x):
        keys = self.x_keys
        data = self.data
        if x in keys:
            return data[x]
        if not len(keys):
            return False
        i = bisect.bisect_left(keys, x)
        if i == 0:
            return data[keys[0]]
        if i >= len(keys):
            return data[keys[i-1]]
        _x = [keys[i-1], keys[i]]
        _y = [data[key] for key in _x]
        return _y[0] + (_y[1] - _y[0]) * ((x - _x[0]) / (_x[1] - _x[0]))
        
