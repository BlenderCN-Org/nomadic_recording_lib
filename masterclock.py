#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# masterclock.py
# Copyright (c) 2010 - 2011 Matthew Reid

import sys
import datetime
import threading

MIDNIGHT = datetime.time()

class MasterClock(object):
    def __init__(self, **kwargs):
        self.clock_interval = kwargs.get('clock_interval', .01)
        self.tick_interval = kwargs.get('tick_interval', .04)
        #self.tick_granularity = len(str(self.tick_interval).split('.')[1])
        self.seconds = None
        callbacks = kwargs.get('callbacks', [])
        self.running = False
        self.timer_id = None
        self.timer = None
        self.tick_listener = None
        self.callbacks = set()
        self.callbacks_to_delete = set()
        self.callback_threads = {}
        self.raw_tick_callbacks = set()
        #self.callback_triggers = {}
        for cb in callbacks:
            self.add_callback(cb)
        #self.ticks = 0

    def calc_seconds(self, dt):
        midnight = datetime.datetime.combine(dt.date(), datetime.time())
        td = dt - midnight
        return td.seconds + (td.microseconds / float(10**6))
        
    @property
    def fps(self):
        return 1.0 / (self.interval / 1000.)
    def start(self):
        self.stop()
#        now = datetime.datetime.now()
#        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
#        td = now - midnight
#        sec = td.seconds + (td.microseconds / float(10**6))
#        self.ticks = sec * 1000 / self.interval
#        self.ticks += 1
        self.running = True
        self._build_timer()
        
        #return self.timer_id
    def stop(self):
        self.running = False
        self._kill_timer()
        self.timer_id = None
        #self.ticks = 0
    
    def add_callback(self, callback, threaded=False):
        if not threaded:
            self.callbacks.add(callback)
            return
        t = ThreadedCallback(clock=self, callback=callback)
        #e = t.trigger
        self.callback_threads[callback] = t
        #self.callback_triggers[callback] = t.trigger
        t.start()
        
    def del_callback(self, callback):
        self.callbacks_to_delete.add(callback)
        
    def add_raw_tick_callback(self, cb):
        self.raw_tick_callbacks.add(cb)
        
    def del_raw_tick_callback(self, cb):
        self.callbacks_to_delete.add(cb)
        
    def _do_remove_callbacks(self):
        for cb in self.callbacks_to_delete:
            self.callbacks.discard(cb)
            if cb in self.callback_threads:
                self.callback_threads[cb].stop()
                del self.callback_threads[cb]
            self.raw_tick_callbacks.discard(cb)
                #del self.callback_triggers[cb]
        #if len(self.callbacks) == 0:
        #    self.stop()
        self.callbacks_to_delete.clear()
        
    def do_callbacks(self):
        seconds = self.seconds
        for t in self.callback_threads.itervalues():
            t.trigger(self, seconds)
        for cb in self.callbacks:
            cb(self, seconds)
            
    def on_timer(self, *args):
        self.now = datetime.datetime.now()
        seconds = self.calc_seconds(self.now)
        self.clock_seconds = seconds
        self._do_remove_callbacks()
        if self.seconds is None:
            cs = seconds - int(seconds)
            for i in range(int(1 / self.tick_interval)):
                ts = i * self.tick_interval
                if ts >= cs:
                    self.seconds = int(seconds) + ts
                    break
        for cb in self.raw_tick_callbacks:
            cb(self, seconds)
        if self.seconds is not None and seconds < self.seconds + self.tick_interval:
            return
        if self.seconds is None:
            return
        self.seconds += self.tick_interval
        self.do_callbacks()
        
    def _build_timer(self):
        self.timer = Ticker(interval=self.clock_interval, callback=self.on_timer)
        self.timer.start()
        
    def _kill_timer(self):
        if self.tick_listener is not None:
            self.tick_listener.stop()
            self.tick_listener = None
        if self.timer is not None:
            self.timer.stop()
            self.timer = None
        

class Ticker(threading.Thread):
    def __init__(self, **kwargs):
        threading.Thread.__init__(self)
        self.interval = kwargs.get('interval')
        self.callback = kwargs.get('callback', self._default_callback)
        self.running = threading.Event()
        self.waiting = threading.Event()
        self.ticking = threading.Event()
        
    def run(self):
        self.running.set()
        while self.running.isSet():
            if not self.running.isSet():
                return
            self.waiting.wait(self.interval)
            self.ticking.set()
            self.callback()
            
    def stop(self):
        self.running.clear()
        
    def _default_callback(self):
        pass
        

class ThreadedCallback(threading.Thread):
    def __init__(self, **kwargs):
        threading.Thread.__init__(self)
        self.running = threading.Event()
        self._trigger_event = threading.Event()
        self.clock = kwargs.get('clock')
        self.callback = kwargs.get('callback')
    def run(self):
        self.running.set()
        while self.running.isSet():
            self._trigger_event.wait()
            if self.running.isSet():
                self.callback(self.clock, self.seconds)
            self._trigger_event.clear()
    def stop(self):
        self.running.clear()
        self._trigger_event.set()
    def trigger(self, clock, seconds):
        #print seconds
        self.seconds = seconds
        self._trigger_event.set()
        

