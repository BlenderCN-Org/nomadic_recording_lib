from BaseObject import BaseObject

class Incrementor(BaseObject):
    _Properties = {'value':dict(default=0, min=0, max=9999, quiet=True), 
                   'resolution':dict(default=1), 
                   'value_offset':dict(default=0)}
    def __init__(self, **kwargs):
        super(Incrementor, self).__init__(**kwargs)
        self.name = kwargs.get('name')
        self.children = {}
        self.register_signal('bounds_reached')
        self.parent = kwargs.get('parent')
        if self.parent is not None:
            self.parent.bind(bounds_reached=self.on_parent_bounds_reached)
        self.value_set_local = False
        self.bind(value=self._on_value_set, 
                  resolution=self._on_resolution_set)
        res = kwargs.get('resolution', getattr(self, '_resolution', None))
        if res is not None:
            self.resolution = res
    def add_child(self, name, cls=None, **kwargs):
        if cls is None:
            cls = Incrementor
        kwargs.setdefault('parent', self)
        kwargs.setdefault('name', name)
        obj = cls(**kwargs)
        self.children[name] = obj
        return obj
    def get_values(self):
        d = self.get_all_obj()
        keys = d.keys()
        return dict(zip(keys, [d[key].value + self.value_offset for key in keys]))
    def set_values(self, **kwargs):
        d = self.get_all_obj()
        for key, val in kwargs.iteritems():
            if key not in d:
                continue
            d[key].value = val - self.value_offset
    def get_all_obj(self, **kwargs):
        d = kwargs.get('d')
        if d is None:
            root = self.get_root_obj()
            d = {}
            kwargs['d'] = d
            root.get_all_obj(d=d)
            return d
        d[self.name] = self
        for key, val in self.children.iteritems():
            val.get_all_obj(d=d)
    def get_root_obj(self):
        if self.parent is not None:
            return self.parent.get_root_obj()
        return self
    def get_root_sum(self, **kwargs):
        root_prop = kwargs.get('root_prop')
        if root_prop is None:
            root = self.get_root_obj()
            rp = root.Properties['value']
            kwargs.update({'root_prop':rp, 'value':rp.value})
            return root.get_root_sum(**kwargs)
        myval = self.value
        for child in self.children.itervalues():
            myval = myval + child.get_root_sum(**kwargs)
        if self.parent is not None:
            d = self.parent.get_range()
            myval = myval * (d['max'] - d['min'] + 1)
        return myval
    def set_root_sum(self, value):
        if self.parent is not None:
            self.parent.set_root_sum(value)
            return
        self.reset_values()
        for i in range(value):
            self += 1
    def reset_values(self, **kwargs):
        root = kwargs.get('root')
        if root is None:
            root = self.get_root_obj()
            kwargs['root'] = root
            root.reset_values(**kwargs)
            return
        self.value_set_local = True
        self.value = self.get_range()['min']
        self.value_set_local = False
        for child in self.children.itervalues():
            child.reset_values(**kwargs)
    def set_range(self, **kwargs):
        for key in ['min', 'max']:
            if key in kwargs:
                setattr(self.Properties['value'], key, kwargs[key])
    def get_range(self):
        return dict(zip(['min', 'max'], self.Properties['value'].range))
    def __add__(self, value):
        prop = self.Properties['value']
        newval = prop.value + value
        if newval > prop.max:
            newval = newval - (prop.max + 1)
            self.emit('bounds_reached', mode='add')
        self.value_set_local = True
        self.value = newval
        self.value_set_local = False
        return self
    def __sub__(self, value):
        prop = self.Properties['value']
        newval = prop.value - value
        if newval < prop.min:
            newval = newval + prop.max
            self.emit('bounds_reached', mode='sub')
        self.value_set_local = True
        self.value = newval
        self.value_set_local = False
        return self
    def on_parent_bounds_reached(self, **kwargs):
        mode = kwargs.get('mode')
        if mode == 'add':
            self += 1
        elif mode == 'sub':
            self -= 1
    def _on_value_set(self, **kwargs):
        if self.value_set_local:
            return
        old = kwargs.get('old')
        value = kwargs.get('value')
    def _on_resolution_set(self, **kwargs):
        self.set_range(min=0, max=self.resolution - 1)
        
class Frame(Incrementor):
    def __init__(self, **kwargs):
        kwargs.setdefault('resolution', 30)
        super(Frame, self).__init__(**kwargs)
        self.add_child('second', Second)
        
class Microsecond(Incrementor):
    _resolution = 10 ** 6
    def __init__(self, **kwargs):
        kwargs.setdefault('name', 'microsecond')
        super(Microsecond, self).__init__(**kwargs)
        self.add_child('second', Second)
        
class Millisecond(Incrementor):
    _resolution = 1000
    def __init__(self, **kwargs):
        kwargs.setdefault('name', 'millisecond')
        super(Millisecond, self).__init__(**kwargs)
        self.add_child('second', Second)
        
class Second(Incrementor):
    _resolution = 60
    def __init__(self, **kwargs):
        super(Second, self).__init__(**kwargs)
        self.add_child('minute', Minute)
    
class Minute(Incrementor):
    _resolution = 60
    def __init__(self, **kwargs):
        super(Minute, self).__init__(**kwargs)
        self.add_child('hour', Hour)
        
class Hour(Incrementor):
    pass
    
if __name__ == '__main__':
    import threading
    import datetime
    import time
    class TestThread(threading.Thread):
        def run(self):
            tick = threading.Event()
            ms = Microsecond()
            self.ms = ms
            #ms.bind(value=self.on_ms)
            all_obj = ms.get_all_obj()
            all_obj['second'].bind(value=self.on_second)
            timeout = .01
            #incr = ms.resolution * timeout
            self.starttime = time.time()
            startdt = datetime.datetime.fromtimestamp(self.starttime)
            while True:
                tick.wait(timeout)
                now = datetime.datetime.now()
                self.now = time.time()
                td = now - startdt
                all_obj['hour'].value = td.seconds / 3600
                all_obj['minute'].value = (td.seconds % 3600) / 60
                all_obj['second'].value = td.seconds % 60
                all_obj['microsecond'].value = td.microseconds
                #elapsed = td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6
                #ms += elapsed
                #lasttime = now
        def on_ms(self, **kwargs):
            print 'microsecond: ', kwargs.get('value')
        def on_second(self, **kwargs):
            print 'seconds=%s, values=%s' % (self.now - self.starttime, self.ms.get_values())
    t = TestThread()
    t.start()
    
    
