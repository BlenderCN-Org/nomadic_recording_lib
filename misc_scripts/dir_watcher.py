#! /usr/bin/env python

import time
import os.path
import argparse

import pyinotify


LOG_START_TS = None
LOG_FILENAME = os.path.join(os.getcwd(), 'dir_watcher.log')

def LOG(*args):
    global LOG_START_TS
    if LOG_START_TS is None:
        LOG_START_TS = time.time()
    ts = time.time() - LOG_START_TS
    line = '%013.6f - %s\n' % (ts, ' '.join([str(arg) for arg in args]))
    with open(LOG_FILENAME, 'a') as f:
        f.write(line)
    

class EventHandler(pyinotify.ProcessEvent):
    def my_init(self, **kwargs):
        self.callback = kwargs.get('callback')
    def process_default(self, event):
        cb = self.callback
        if cb is None:
            return
        cb(event)

def build_mask(*args):
    mask = 0
    for arg in args:
        if isinstance(arg, basestring):
            arg = getattr(pyinotify, arg)
        mask |= arg
    return mask
    
def build_notifier(**kwargs):
    wm = pyinotify.WatchManager()
    mask = kwargs.get('mask', 0)
    events = kwargs.get('events')
    if events:
        if type(events) not in [list, tuple, set]:
            events = [events]
        mask |= build_mask(*events)
    path = kwargs.get('path')
    callback = kwargs.get('callback')
    run_loop = kwargs.get('run_loop', True)
    handler = EventHandler(callback=callback)
    notifier = pyinotify.Notifier(wm, handler)
    wm.add_watch(path, mask)
    if run_loop:
        notifier.loop()
    else:
        return {'handler':handler, 'notifier':notifier}

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('-p', dest='path')
    p.add_argument('--logfile', dest='logfile')
    p.add_argument('-e', dest='events', action='append')
    args, remaining = p.parse_known_args()
    o = vars(args)
    if not o.get('path'):
        o['path'] = os.getcwd()
    if o.get('logfile'):
        LOG_FILENAME = o['logfile']
    if not o.get('events'):
        o['events'] = 'IN_CLOSE_WRITE'
    mask = 0
    for event in o['events']:
        mask |= getattr(pyinotify, event)
    o['mask'] = mask
    build_notifier(**o)
