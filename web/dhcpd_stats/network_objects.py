from parser import LeaseConf

NETWORKS = []
LEASES = []

class IPAddress(object):
    def __init__(self, address_str):
        self._value = None
        self.address_str = address_str
        self.quad = [int(q) for q in address_str.split('.')]
    @property
    def value(self):
        v = self._value
        if v is None:
            v = 0
            l = [16777216, 65536, 256, 1]
            for o, m in zip(self.quad, l):
                v += o * m
            self._value = v
        return v
    def __hash__(self):
        return self.value
    def __cmp__(self, other):
        if self.value > other.value:
            return 1
        if self.value < other.value:
            return -1
        return 0
    def __str__(self):
        return self.address_str
        
class NetworkBase(object):
    def __init__(self, **kwargs):
        self.parent = kwargs.get('parent')
        self.conf_object = kwargs.get('conf_object')
    def add_child_from_conf(self, cls, conf_obj, **kwargs):
        kwargs['conf_object'] = conf_obj
        kwargs['parent'] = self
        return cls(**kwargs)
        
class Network(NetworkBase):
    def __init__(self, **kwargs):
        super(Network, self).__init__(**kwargs)
        self.subnets = {}
        for k, v in self.conf_object.subnets.iteritems():
            subnet = self.add_child_from_conf(Subnet, v)
            self.subnets[subnet.address] = subnet
    @property
    def name(self):
        return self.conf_object.name
    @property
    def total_addresses(self):
        i = 0
        for subnet in self.subnets.itervalues():
            i += subnet.total_addresses
        return i
    @property
    def available_addresses(self):
        i = 0
        for subnet in self.subnets.itervalues():
            i += subnet.available_addresses
        return i
    def match_address(self, address):
        if isinstance(address, basestring):
            address = IPAddress(address)
        for subnet in self.subnets.itervalues():
            if subnet.match_address(address):
                return True
        return False
    def add_lease(self, lease):
        for subnet in self.subnets.itervalues():
            added = subnet.add_lease(lease)
            if added:
                return True
        return False
    def remove_lease(self, lease):
        for subnet in self.subnets.itervalues():
            removed = subnet.remove_lease(lease)
            if removed:
                return True
        return False
    def __repr__(self):
        return 'Network: %s' % (self)
    def __str__(self):
        return self.name
        
class Subnet(NetworkBase):
    def __init__(self, **kwargs):
        super(Subnet, self).__init__(**kwargs)
        self.address = IPAddress(self.conf_object.address)
        self.ranges = []
        for pool in self.conf_object.pools:
            for r in pool.ranges:
                robj = self.add_child_from_conf(Range, r)
                self.ranges.append(robj)
    @property
    def total_addresses(self):
        i = 0
        for r in self.ranges:
            i += r.total_addresses
        return i
    @property
    def available_addresses(self):
        i = 0
        for r in self.ranges:
            i += r.available_addresses
        return i
    def match_address(self, address):
        if isinstance(address, basestring):
            address = IPAddress(address)
        for r in self.ranges:
            if r.match_address(address):
                return True
        return False
    def add_lease(self, lease):
        for r in self.ranges:
            added = r.add_lease(lease)
            if added:
                return True
        return False
    def remove_lease(self, lease):
        for r in self.ranges:
            removed = r.remove_lease(lease)
            if removed:
                return True
        return False
    def __repr__(self):
        return 'Subnet %s' % (self)
    def __str__(self):
        return str(self.address)
        
class Range(NetworkBase):
    def __init__(self, **kwargs):
        super(Range, self).__init__(**kwargs)
        self.start = IPAddress(self.conf_object.start)
        self.end = IPAddress(self.conf_object.end)
        self.total_addresses = self.end.value - self.start.value
        self.leases = {}
    @property
    def available_addresses(self):
        return self.total_addresses - len(self.leases)
    def match_address(self, address):
        if isinstance(address, basestring):
            address = IPAddress(address)
        if address < self.start:
            return False
        if address > self.end:
            return False
        return True
    def add_lease(self, lease):
        if not self.match_address(lease.address):
            return False
        key = lease.address
        if key in self.leases:
            if lease is self.leases[key]:
                return True
            if lease.start_time < self.leases[key].start_time:
                return False
        self.leases[key] = lease
        return True
    def remove_lease(self, lease):
        key = lease.address
        if key not in self.leases:
            return False
        del self.leases[key]
        return True
    def __repr__(self):
        return 'Range: %s' % (self)
    def __str__(self):
        return '%s - %s' % (self.start, self.end)
    
class Lease(LeaseConf):
    def __init__(self, **kwargs):
        self._network_obj = None
        super(Lease, self).__init__(**kwargs)
        self.address = IPAddress(self.address)
        self.network_obj = kwargs.get('network_obj')
        if self.network_obj is None:
            self.network_obj = self.find_network()
    @property
    def network_obj(self):
        return self._network_obj
    @network_obj.setter
    def network_obj(self, value):
        if value == self._network_obj:
            return
        if self._network_obj is not None:
            self._network_obj.remove_lease(self)
        self._network_obj = value
        if value is not None:
            value.add_lease(self)
    @classmethod
    def from_conf(cls, conf_obj, **kwargs):
        new_kwargs = kwargs.copy()
        for attr in cls._conf_attrs:
            new_kwargs[attr] = getattr(conf_obj, attr)
        return cls(**new_kwargs)
    def find_network(self):
        global NETWORKS
        for n in NETWORKS:
            if n.match_address(self.address):
                return n
        
def build_networks(conf_networks):
    global NETWORKS
    for cnet in conf_networks:
        NETWORKS.append(Network(conf_object=cnet))
    return NETWORKS
def build_leases(conf_leases):
    global LEASES
    for clease in conf_leases:
        LEASES.append(Lease.from_conf(clease))
    return LEASES
