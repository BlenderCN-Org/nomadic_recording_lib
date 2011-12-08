import threading
import time

class Scheduler(threading.Thread):
    def __init__(self, **kwargs):
        threading.Thread.__init__(self)
        self.callback = kwargs.get('callback')
        self.spawn_threads = kwargs.get('spawn_threads', False)
        if self.spawn_threads:
            self._do_callback = self.do_threaded_callback
        else:
            self._do_callback = self.do_callback
        self.running = threading.Event()
        self.waiting = threading.Event()
        self.next_timeout = None
        self.queue = TimeQueue()
        
    def now(self):
        return time.time()
        
    def add_item(self, time, item):
        self.queue.put(time, item)
        self.waiting.set()
        
    def run(self):
        self.running.set()
        while self.running.isSet():
            self.waiting.wait(self.next_timeout)
            if not self.running.isSet():
                return
            if not len(self.queue.times):
                self.waiting.clear()
                self.next_timeout = None
            else:
                if self.next_timeout is not None:
                    self.process_next_item()
                else:
                    timeout, t = self.time_to_next_item()
                    #print '%011.8f, %011.8f' % (timeout, t)
                    if timeout <= 0:
                        #self.process_item(t)
                        self.process_next_item()
                        self.waiting.set()
                    else:
                        self.waiting.clear()
                        self.next_timeout = timeout
                        #print 'scheduler waiting: t=%010.8f, diff=%010.8f' % (t, timeout)
            
    def stop(self):
        self.running.clear()
        self.waiting.set()
        
    def process_item(self, time):
        t, item = self.queue.pop(time)
        self._do_callback(item, time)
        
    def process_next_item(self):
        #now = self.now()
        queue = self.queue.pop()
        if not queue:
            return
        t, item = queue
        #print 'scheduler processing: t=%010.8f, now=%010.8f, diff=%010.8f' % (t, now, t - now)
        self._do_callback(item, t)
        
    def do_callback(self, *args, **kwargs):
        self.callback(*args, **kwargs)
        
    def do_threaded_callback(self, *args, **kwargs):
        t = threading.Thread(target=self.callback, args=args, kwargs=kwargs)
        t.start()
            
    def time_to_next_item(self):
        t = self.queue.lowest_time()
        if t is None:
            return False
        return (t - self.now(), t)
        
class TimeQueue(object):
    def __init__(self, **kwargs):
        self.times = set()
        self.data = {}
        
    def put(self, time, item):
        self.times.add(time)
        data = self.data.get(time, [])
        data.append(item)
        self.data[time] = data
        
    def pop(self, t=None):
        if t is None:
            t = self.lowest_time()
        if t is None:
            return t
        data = self.data.get(t)
        if data is None:
            self.times.discard(t)
            return None
        item = data.pop()
        if not len(data):
            del self.data[t]
            self.times.discard(t)
        return (t, item)
        
    def lowest_time(self):
        if not len(self.times):
            return None
        return sorted(self.times)[0]
