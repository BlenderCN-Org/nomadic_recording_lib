import time
import datetime

from threadbases import BaseThread

class Scheduler(BaseThread):
    _Events = {'waiting':{}}
    def __init__(self, **kwargs):
        super(Scheduler, self).__init__(**kwargs)
        time_method = kwargs.get('time_method', 'timestamp')
        if isinstance(time_method, basestring):
            if not callable(getattr(self, time_method, None)):
                time_method = '_now_%s' % (time_method)
            m = getattr(self, time_method)
        else:
            m = time_method
        self.now = m
        self.callback = kwargs.get('callback')
        self.spawn_threads = kwargs.get('spawn_threads', False)
        if self.spawn_threads:
            self._do_callback = self.do_threaded_callback
        else:
            self._do_callback = self.do_callback
        self.queue = TimeQueue()
        
    def _now_timestamp(self):
        return time.time()
    def _now_datetime(self):
        return datetime.datetime.now()
    def _now_datetime_utc(self):
        return datetime.datetime.utcnow()
        
    def add_item(self, time, item):
        self.queue.put(time, item)
        self.waiting.set()
        
    def run(self):
        #running = self._running
        #waiting = self.waiting
        next_timeout = None
        queue = self.queue
        time_to_next_item = self.time_to_next_item
        process_next_item = self.process_next_item
        get_now = self.now
        self._running = True
        while self._running:
            self.waiting.wait(next_timeout)
            if not self._running:
                break
            if not len(queue.times):
                self.waiting = False
                next_timeout = None
            else:
                if next_timeout is not None:
                    process_next_item()
                else:
                    timeout, t = time_to_next_item()
                    #print '%011.8f, %011.8f' % (timeout, t)
                    if timeout <= 0:
                        #self.process_item(t)
                        process_next_item()
                        self.waiting = True
                    else:
                        self.waiting = False
                        next_timeout = timeout
                        #print 'scheduler waiting: t=%010.8f, diff=%010.8f' % (t, timeout)
        self._stopped = True
        
    def stop(self, **kwargs):
        self._running = False
        self.waiting = True
        super(Scheduler, self).stop(**kwargs)
        
    def process_item(self, time):
        t, item = self.queue.pop(time)
        self._do_callback(item, time)
        
    def process_next_item(self):
        now = self.now()
        data = self.queue.pop()
        if not data:
            return
        t, item = data
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
            return False, False
        result = t - self.now()
        if isinstance(result, datetime.timedelta):
            if hasattr(result, 'total_seconds'):
                result = result.total_seconds()
            else:
                td = result
                result = (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / 10**6
        return (result, t)
        
class TimeQueue(object):
    def __init__(self, **kwargs):
        self.times = set()
        self.data = {}
        
    def put(self, time, item):
        self.times.add(time)
        data = self.data.get(time, [])
        data.append(item)
        self.data[time] = data
        
    def remove(self, **kwargs):
        def do_remove(t, item):
            data = self.data.get(t)
            if data is None:
                return False
            if item not in data:
                return False
            data.remove(item)
            if not len(data):
                del self.data[t]
                self.times.discard(t)
            return True
        item = kwargs.get('item')
        t = kwargs.get('time')
        if t is not None:
            return do_remove(t, item)
        for key, val in self.data.iteritems():
            if item in val:
                return do_remove(key, item)
        return False
        
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
        return min(self.times)
        
    def __len__(self):
        return len(self.times)
