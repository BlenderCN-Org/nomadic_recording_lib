import os
import datetime
import json
import argparse

from config import config
import parser
import network_objects

def do_parse():
    net_conf = parser.parse_conf()
    lease_conf = parser.parse_leases()
    nets = network_objects.build_networks(net_conf)
    network_objects.build_leases(lease_conf)
    return nets
    
def log_all(nets=None):
    if nets is None:
        nets = do_parse()
    d = {}
    for n in nets:
        d[n.name] = n.serialize()
    s = json.dumps(d)
    now = datetime.datetime.now()
    fn = now.strftime(config.log_file_format)
    p = os.path.expanduser(config.log_file_path)
    if not os.path.exists(p):
        os.makedirs(p)
    with open(os.path.join(p, fn), 'w') as f:
        f.write(s)
    return nets
        
def log_stats(nets=None):
    if nets is None:
        nets = do_parse()
    d = {}
    for n in nets:
        d[n.name] = n.serialize(include_leases=False)
    now = datetime.datetime.now()
    fn = 'stats.json'
    p = os.path.expanduser(config.log_file_path)
    if not os.path.exists(p):
        os.makedirs(p)
    fn = os.path.join(p, fn)
    if os.path.exists(fn):
        with open(fn, 'r') as f:
            s = f.read()
        _d = json.loads(s)
    else:
        _d = {}
    _d[str(now)] = d
    s = json.dumps(_d)
    with open(os.path.join(p, fn), 'w') as f:
        f.write(s)
    return nets
        
if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--stats-only', dest='stats_only', action='store_true')
    args, remaining = p.parse_known_args()
    o = vars(args)
    nets = log_stats()
    if not o.get('stats_only'):
        log_all()
