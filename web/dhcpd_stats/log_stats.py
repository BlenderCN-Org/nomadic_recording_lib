import os
import datetime
import json

from config import config
import parser
import network_objects

def main():
    net_conf = parser.parse_conf()
    lease_conf = parser.parse_leases()
    nets = network_objects.build_networks(net_conf)
    network_objects.build_leases(lease_conf)
    d = {}
    for n in nets:
        d[n.name] = n.serialize()
    s = json.dumps(d)
    now = datetime.datetime.now()
    fn = os.path.expanduser(now.strftime(config.log_file_format))
    if not os.path.exists(os.path.dirname(fn)):
        os.makedirs(os.path.dirname(fn))
    with open(fn, 'w') as f:
        f.write(s)
        
if __name__ == '__main__':
    main()
