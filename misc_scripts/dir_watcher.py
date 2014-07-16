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
    def process_default(self, event):
        LOG(repr(event))

def loop_callback(wm):
    LOG('loop')

def build_notifier(**kwargs):
    wm = pyinotify.WatchManager()
    mask = kwargs.get('mask')
    path = kwargs.get('path')
    handler = EventHandler()
    notifier = pyinotify.Notifier(wm, handler)
    wdd = wm.add_watch(path, mask)
    notifier.loop(callback=loop_callback)

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('-p', dest='path')
    p.add_argument('--logfile', dest='logfile')
    args, remaining = p.parse_known_args()
    o = vars(args)
    if not o.get('path'):
        o['path'] = os.getcwd()
    if o.get('logfile'):
        LOG_FILENAME = o['logfile']
    o['mask'] = pyinotify.ALL_EVENTS
    build_notifier(**o)
