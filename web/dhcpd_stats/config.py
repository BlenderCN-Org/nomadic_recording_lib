import os
import json

CONF_FILENAME = os.path.expanduser('~/.dhcpd_stats')

class Config(object):
    dhcpd_conf = '/etc/dhcp/dhcpd.conf'
    dhcpd_leases = '/var/lib/dhcp/dhcpd.leases'
    log_file_format = '~/dhcpd_stats/%Y%m%d_%H%M.json'
    def __init__(self, **kwargs):
        for k, v in kwargs.iteritems():
            setattr(self, k, v)
    @classmethod
    def from_json(cls, filename):
        with open(filename, 'r') as f:
            s = f.read()
        d = json.loads(s)
        return cls(**d)
    

if os.path.exists(CONF_FILENAME):
    config = Config.from_json(CONF_FILENAME)
else:
    config = Config()
