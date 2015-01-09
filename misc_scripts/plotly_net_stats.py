import time
import threading
import datetime
import plotly.plotly as py
import plotly.tools as tls
import plotly.graph_objs as py_graph_objs

import net_stats

class PlotlyError(Exception):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return repr(self.msg)
class PlotlyStreamContextError(PlotlyError):
    def __init__(self, stream):
        self.msg = 'Stream %r must be open before writing' % (stream)

STREAMS = {}
STREAMS_BY_ID = {}
STREAMS_BY_TRACE_NAME = {}
def build_streams():
    global STREAMS, STREAMS_BY_ID
    stream_ids = tls.get_credentials_file()['stream_ids']
    for i, stream_id in enumerate(stream_ids):
        if stream_id in STREAMS_BY_ID:
            s = STREAMS_BY_ID[stream_id]
            if s.index != i:
                if s.index in STREAMS:
                    del STREAMS[s.index]
                s.index = i
                STREAMS[i] = s
            continue
        s = Stream(id=stream_id, index=i)
        STREAMS[i] = s
        STREAMS_BY_ID[s.id] = s

def get_next_available_stream():
    for stream_index in sorted(STREAMS.keys()):
        s = STREAMS[stream_index]
        if s.trace is None:
            return s
    
class Stream(object):
    def __init__(self, **kwargs):
        self._trace = None
        self.id = kwargs.get('id')
        self.index = kwargs.get('index')
        self.trace = kwargs.get('trace')
        self._stream = None
        self._last_write = None
        self._disconnect_timer = None
    @property
    def stream(self):
        s = self._stream
        if s is None or s.exited:
            s = self._stream = StreamIO(self)
        return s
    @property
    def trace(self):
        return self._trace
    @trace.setter
    def trace(self, value):
        if value == self._trace:
            return
        if self._trace is not None:
            if self._trace.name in STREAMS_BY_TRACE_NAME:
                del STREAMS_BY_TRACE_NAME[self._trace.name]
        self._trace = value
        if value is not None:
            STREAMS_BY_TRACE_NAME[value.name] = self
    def _rebuild_disconnect_timer(self):
        self._last_write = time.now()
        t = self._disconnect_timer
        if t is not None and t.is_alive():
            t.cancel()
        t = self._disconnect_timer = threading.Timer(30., self._disconnect_timer_cb)
        t.start()
    def _disconnect_timer_cb(self):
        s = self._stream
        s.needs_close = True
        self._disconnect_timer = None
    def write(self, data):
        s = self.stream
        with s:
            s.write(data)
    def __repr__(self):
        return str(self)
    def __str__(self):
        return 'Stream (id=%s, index=%s)' % (self.id, self.index)
    
class StreamIO(object):
    def __init__(self, stream):
        self.stream = stream
        self.py_stream = None
        self.is_open = False
        self.needs_close = False
        self.exited = False
        self._entry_count = 0
    def write(self, data):
        if not self.is_open:
            raise PlotlyStreamContextError(self.stream)
        self.py_stream.write(data)
    def __enter__(self):
        self._entry_count += 1
        if self.is_open:
            return
        if self.py_stream is None:
            self.py_stream = py.Stream(self.stream.id)
        self.py_stream.open()
        self.is_open = True
    def __exit__(self, exc_type, exc_val, exc_tb):
        self._entry_count -= 1
        if self._entry_count > 0:
            return
        if self.is_open and self.needs_close:
            self.py_stream.close()
            #self.py_stream = None
            self.is_open = False
            #self.exited = True
    def __repr__(self):
        return str(self)
    def __str__(self):
        return 'StreamIO of <%s>' % (self.stream)

build_streams()

class Trace(object):
    def __init__(self, **kwargs):
        self.name = kwargs.get('name')
        self.stream_index = kwargs.get('stream_index')
        if self.stream_index is None:
            self.stream = get_next_available_stream()
            self.stream_index = self.stream.index
        else:
            self.stream = STREAMS[self.stream_index]
        self.stream.trace = self
        self.trace = py_graph_objs.Scatter(x=[], 
                                           y=[], 
                                           name=self.name, 
                                           stream={'token':self.stream.id})
    def write(self, data):
        self.stream.write(data)
    def __repr__(self):
        return str(self)
    def __str__(self):
        return 'Trace (%s)' % (self.name)
        
class Plotter(object):
    def __init__(self, **kwargs):
        self.title = kwargs.get('title')
        self.trace_names = kwargs.get('trace_names')
        self.filename = kwargs.get('filename')
        self.fileopt = kwargs.get('fileopt', 'extend')
        self.traces = {}
        for name in self.trace_names:
            trace = Trace(name=name)
            self.traces[trace.name] = trace
        self.data = py_graph_objs.Data([t.trace for t in self.iter_traces()])
        self.layout = py_graph_objs.Layout(title=self.title)
        self.figure = py_graph_objs.Figure(data=self.data, layout=self.layout)
        self.url = py.plot(self.figure, filename=self.filename, fileopt=self.fileopt, auto_open=False)
    def iter_traces(self):
        for name in self.trace_names:
            yield self.traces[name]
    def write(self, trace_name, data):
        self.traces[trace_name].write(data)
    def __repr__(self):
        return str(self)
    def __str__(self):
        return 'Plotter (%s)' % (self.title)

class Main(object):
    def __init__(self, **kwargs):
        self.filename_prefix = kwargs.get('filename_prefix', '')
        self.interface_names = kwargs.get('interface_names')
        self.plots = {}
        for name in self.interface_names:
            p = Plotter(title=name, 
                        filename=''.join([self.filename_prefix, name]), 
                        trace_names=['tx', 'rx'])
            self.plots[name] = p
    def on_net_stat_update(self, **kwargs):
        dt = datetime.datetime.fromtimestamp(kwargs.get('timestamp'))
        dt_str = str(dt)
        obj = kwargs.get('obj')
        plot = self.plots[obj.name]
        for key in ['tx', 'rx']:
            val = kwargs['data']['data']['current_%s' % (key)]
            #print obj.name, key, val
            plot.write(key, {'x':dt_str, 'y':val})

def main(**kwargs):
    pl_main = None
    def on_net_stat_update(**kwargs):
        if pl_main is None:
            return
        pl_main.on_net_stat_update(**kwargs)
    kwargs.setdefault('output_type', 'callback')
    kwargs.setdefault('output_callback', on_net_stat_update)
    kwargs['auto_start'] = False
    ns_main = net_stats.main(**kwargs)
    pl_main = Main(interface_names=ns_main.interface_names)
    ns_main.start(join=True)
    
if __name__ == '__main__':
    main()
