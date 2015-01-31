import os
import json
import datetime

import pytz

CONF_FILENAME = os.path.expanduser('~/.dhcpd_stats')

class Config(object):
    dhcpd_conf = '/etc/dhcp/dhcpd.conf'
    dhcpd_leases = '/var/lib/dhcp/dhcpd.leases'
    log_file_path = '~/dhcpd_stats/'
    log_file_format = '%Y%m%d_%H%M.json'
    server_timezone_name = 'US/Central'
    def __init__(self, **kwargs):
        self._now = None
        self._server_timezone = None
        for k, v in kwargs.iteritems():
            setattr(self, k, v)
    @property
    def now(self):
        now = self._now
        if now is None:
            now = datetime.datetime.utcnow()
            now = pytz.utc.localize(now)
            self._now = now
        return now
    @property
    def server_timezone(self):
        tz = self._server_timezone
        if tz is None:
            tz = self._server_timezone = pytz.timezone(self.server_timezone_name)
        return tz
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
