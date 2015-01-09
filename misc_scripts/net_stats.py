#! /usr/bin/env python

import argparse
import time
import threading
import json

class Interface(object):
    _stats_file_fmt = '/sys/class/net/%(name)s/statistics/%(io_type)s_bytes'
    fields = ['total_rx', 'total_tx', 'current_rx', 'current_tx']
    def __init__(self, **kwargs):
        self.name = kwargs.get('name')
        self.interval = kwargs.get('interval', 1.)
        self.update_callback = kwargs.get('update_callback')
        self.last_update = None
        self.total_io_bytes = {'rx':0, 'tx':0}
        self.current_io_bytes = {'rx':0, 'tx':0}
    @property
    def total_rx(self):
        return self.total_io_bytes['rx']
    @property
    def total_tx(self):
        return self.total_io_bytes['tx']
    @property
    def current_rx(self):
        return self.current_io_bytes['rx']
    @property
    def current_tx(self):
        return self.current_io_bytes['tx']
    def get_total_bytes(self, io_type):
        fn = self._stats_file_fmt % dict(name=self.name, io_type=io_type)
        with open(fn, 'r') as f:
            s = f.read()
        return int(s)
    def on_interval(self, now):
        last_update = self.last_update
        if last_update is not None:
            if now - last_update < self.interval:
                return
        self.last_update = now
        for io_type in ['rx', 'tx']:
            total_bytes = self.get_total_bytes(io_type)
            if last_update is not None:
                self.current_io_bytes[io_type] = total_bytes - self.total_io_bytes[io_type]
            self.total_io_bytes[io_type] = total_bytes
        self.on_data_update(timestamp=now)
    def on_data_update(self, **kwargs):
        cb = self.update_callback
        if cb is None:
            return
        data = {
            'fields':self.fields, 
            'obj_type':'Interface', 
            'obj_name':self.name, 
            'data':{}, 
        }
        for field in self.fields:
            data['data'][field] = getattr(self, field)
        kwargs['data'] = data
        kwargs['obj'] = self
        cb(**kwargs)
    
class Scheduler(object):
    def __init__(self, **kwargs):
        self.interval = kwargs.get('interval', 1.)
        self.running = False
        self.callbacks = set()
        update_objects = kwargs.get('update_objects', [])
        callbacks = kwargs.get('callbacks', [])
        for obj in update_objects:
            self.add_update_object(obj)
        for cb in callbacks:
            self.add_callback(cb)
    def start(self, join=False):
        self.running = True
        self.schedule_next()
        if join:
            self.join()
    def stop(self):
        self.running = False
    def join(self):
        pass
    def schedule_next(self):
        pass
    def add_update_object(self, obj):
        if obj.interval < self.interval:
            self.interval = obj.interval
        self.add_callback(obj.on_interval)
    def add_callback(self, cb):
        self.callbacks.add(cb)
    def on_interval(self, *args, **kwargs):
        now = time.time()
        for cb in self.callbacks:
            cb(now)
        if self.running:
            self.schedule_next()
            
class BlockingScheduler(Scheduler):
    def schedule_next(self):
        time.sleep(self.interval)
        self.on_interval()
        
class ThreadedScheduler(Scheduler):
    def start(self, join=False):
        self.timer_thread = TimerThread(scheduler=self)
        self.timer_thread.start()
        super(ThreadedScheduler, self).start(join)
    def stop(self):
        self.timer_thread.stop()
        self.running = False 
    def join(self):
        try:
            while self.running:
                time.sleep(1.)
        except KeyboardInterrupt:
            self.stop()
        
class TimerThread(threading.Thread):
    def __init__(self, **kwargs):
        super(TimerThread, self).__init__()
        self.scheduler = kwargs.get('scheduler')
        self.running = threading.Event()
        self.waiting = threading.Event()
        self.stopped = threading.Event()
    def run(self):
        self.running.set()
        while self.running.is_set():
            self.waiting.wait(self.scheduler.interval)
            if not self.waiting.is_set():
                self.scheduler.on_interval()
        self.stopped.set()
    def stop(self):
        self.running.clear()
        self.waiting.set()
        self.stopped.wait()
    
class OutputHandler(object):
    def __init__(self, **kwargs):
        self.output_format = kwargs.get('output_format')
    def handle_output(self, **kwargs):
        output = self.format_output(kwargs.get('data'))
        self.write(output)
    def format_output(self, data):
        fmt = self.output_format
        if fmt == 'json':
            return json.dumps(data)
        elif fmt in ['csv', 'tsv']:
            if fmt == 'csv':
                delim = ','
            else:
                delim = '\t'
            fields = data['fields']
            lines = []
            lines.append('#obj_type: %s' % (data['obj_type']))
            lines.append('#obj_name: %s' % (data['obj_name']))
            lines.append(delim.join(fields))
            lines.append(delim.join([str(data['data'][key]) for key in fields]))
            return '\n'.join(lines)
class ConsoleOutput(OutputHandler):
    def write(self, output):
        print output
class FileOutput(OutputHandler):
    def __init__(self, **kwargs):
        super(FileOutput, self).__init__(**kwargs)
        self.filename = kwargs.get('output_filename')
    def write(self, output):
        with open(self.filename, 'w') as f:
            f.write(output)
class CallbackOutput(OutputHandler):
    def __init__(self, **kwargs):
        super(CallbackOutput, self).__init__(**kwargs)
        self.callback = kwargs.get('output_callback')
    def handle_output(self, **kwargs):
        cb = self.callback
        if cb is not None:
            cb(**kwargs)
            
OUTPUT_HANDLERS = {'console':ConsoleOutput, 'file':FileOutput, 'callback':CallbackOutput}

class Main(object):
    def __init__(self, **kwargs):
        self.interface_names = kwargs.get('net_devs')
        self.interval = kwargs.get('update_interval', 1.)
        cls = OUTPUT_HANDLERS.get(kwargs.get('output_type'))
        self.output_handler = cls(**kwargs)
        if kwargs.get('scheduler_type') == 'blocking':
            cls = BlockingScheduler
        else:
            cls = ThreadedScheduler
        self.scheduler = cls(interval=self.interval)
        self.interfaces = {}
        for name in self.interface_names:
            self.add_interface(name)
    def start(self, join=False):
        self.scheduler.start(join)
    def stop(self):
        self.scheduler.stop()
    def add_interface(self, name):
        obj = Interface(name=name, interval=self.interval, update_callback=self.on_interface_update)
        self.interfaces[name] = obj
        self.scheduler.add_update_object(obj)
    def on_interface_update(self, **kwargs):
        self.output_handler.handle_output(**kwargs)
        
def main(**kwargs):
    auto_start = kwargs.get('auto_start', True)
    p = argparse.ArgumentParser()
    p.add_argument('--net', dest='net_devs', action='append')
    p.add_argument('--output-type', 
                   dest='output_type', 
                   choices=['file', 'console'], 
                   default='console')
    p.add_argument('--output-format', 
                   dest='output_format', 
                   choices=['json', 'csv', 'tsv'], 
                   default='tsv')
    p.add_argument('--output-filename', dest='output_filename')
    p.add_argument('--update-interval', dest='update_interval', default='1.0', type=float)
    p.add_argument('--scheduler-type', 
                   dest='scheduler_type',
                   choices=['blocking', 'threaded'], 
                   default='threaded')
    args, remaining = p.parse_known_args()
    o = vars(args)
    o.update(kwargs)
    obj = Main(**o)
    if auto_start:
        obj.start(join=True)
    return obj
    
if __name__ == '__main__':
    main()
    
