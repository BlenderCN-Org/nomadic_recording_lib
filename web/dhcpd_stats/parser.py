import datetime

class ParsedSection(object):
    def __init__(self, **kwargs):
        self.parent_section = kwargs.get('parent_section')
        self.start_line_num = kwargs.get('start_line_num')
        self.end_line_num = None
        conf_lines = kwargs.get('conf_lines')
        if isinstance(conf_lines, basestring):
            conf_lines = conf_lines.splitlines()
        elif conf_lines is None:
            conf_lines = self.parent_section.conf_lines
        self.conf_lines = conf_lines
        self.child_sections = {}
        self.search_brackets()
    @property
    def start_line(self):
        return self.conf_lines[self.start_line_num]
    def iter_children(self):
        for i in sorted(self.child_sections.keys()):
            yield self.child_sections[i]
    def search_brackets(self):
        open_brackets = 0
        bracket_found = False
        def add_child(line_num):
            child = ParsedSection(parent_section=self, start_line_num=line_num)
            self.child_sections[line_num] = child
        start_line = self.start_line_num
        if start_line is None:
            start_line = 0
        my_line_found = False
        for i, line in self.iter_lines(start_line):
            if '{' in line:
                open_brackets += 1
                bracket_found = True
                if open_brackets == 1:
                    ## this line belongs to me
                    if not my_line_found:
                        self.start_line_num = i
                        my_line_found = True
                    continue
                add_child(i)
            elif '}' in line:
                open_brackets -= 1
                if open_brackets == 0:
                    self.end_line_num = i
                    break
    def iter_lines(self, start_line=None):
        lines = self.conf_lines
        if start_line is None:
            start_line = self.start_line_num
        end_line = self.end_line_num
        if end_line is None:
            end_line = len(lines) - 1
        for i in range(start_line, end_line):
            yield i, lines[i]
    def serialize(self):
        d = {'line':self.start_line.strip(), 'line_num':self.start_line_num}
        children = []
        for c in self.iter_children():
            children.append(c.serialize())
        if len(children):
            d['children'] = children
        return d
    def __str__(self):
        return '(%03d-%03d) - %s' % (self.start_line_num, self.end_line_num, self.start_line.strip())
        
class ParseBase(object):
    def __init__(self, **kwargs):
        self.parent = kwargs.get('parent')
        self.parsed_section = kwargs.get('parsed_section')
        from_parse = kwargs.get('from_parse')
        if from_parse:
            self.parse_start_line(self.start_line)
    @property
    def start_line(self):
        return self.parsed_section.start_line.strip()
    def parse_children(self, cls):
        ckwargs = {'parent':self}
        def walk_children(section):
            is_first = True
            for schild in section.iter_children():
                if is_first:
                    to_yield = schild
                    is_first = False
                elif len(schild.child_sections):
                    for gchild in walk_children(schild):
                        to_yield = gchild
                else:
                    to_yield = None
                if to_yield is None:
                    break
                yield to_yield
        for pchild in walk_children(self.parsed_section):
            ckwargs['parsed_section'] = pchild
            chobj = cls._parse(**ckwargs)
            if chobj is False:
                continue
            yield chobj
    @classmethod
    def _parse(cls, **kwargs):
        psect = kwargs.get('parsed_section')
        start_line = psect.start_line.strip()
        if cls.conf_keyword not in start_line:
            return False
        objkwargs = kwargs.copy()
        objkwargs['start_line'] = start_line
        objkwargs['from_parse'] = True
        return cls(**objkwargs)
    def parse_start_line(self):
        pass
        
class NetworkConf(ParseBase):
    conf_keyword = 'shared-network'
    def __init__(self, **kwargs):
        self.name = kwargs.get('name')   
        super(NetworkConf, self).__init__(**kwargs)
        self.subnets = {}
        if self.parsed_section is not None:
            for subnet in self.parse_children(SubnetConf):
                self.subnets[subnet.address] = subnet
    def parse_start_line(self, line):
        line = line.split(' ')
        self.name = line[1]
    def serialize(self):
        d = {'name':self.name, 'subnets':{}}
        for k, v in self.subnets.iteritems():
            d['subnets'][k] = v.serialize()
        return d
    def __str__(self):
        return 'network: %s' % self.name
    
class SubnetConf(ParseBase):
    conf_keyword = 'subnet'
    def __init__(self, **kwargs):
        self.address = kwargs.get('address')
        self.netmask = kwargs.get('netmask')
        super(SubnetConf, self).__init__(**kwargs)
        if self.parent is None:
            self.parent = NetworkConf(name='unknown')
            self.parent.subnets[self.address] = self
        self.pools = []
        print str(self)
        #print self.parsed_section.serialize()
        for p in self.parse_children(PoolConf):
            self.pools.append(p)
    def parse_start_line(self, line):
        line = line.split(' ')
        self.address = line[1]
        self.netmask = line[3]
    def serialize(self):
        d = {'address':self.address, 'netmask':self.netmask, 'pools':[]}
        for v in self.pools:
            d['pools'].append(v.serialize())
        return d
    def __str__(self):
        return 'subnet: %s' % (self.address)
    
class PoolConf(ParseBase):
    conf_keyword = 'pool'
    def __init__(self, **kwargs):
        self.ranges = []
        super(PoolConf, self).__init__(**kwargs)
    def parse_start_line(self, line):
        for i, line in self.parsed_section.iter_lines():
            #print '%02d - %s' % (i, line)
            if 'range' not in line:
                continue
            r = RangeConf(parent=self)
            r.parse_start_line(line)
            self.ranges.append(r)
    def serialize(self):
        d = {'ranges':[]}
        for r in self.ranges:
            d['ranges'].append(r.serialize())
        return d
            
class RangeConf(ParseBase):
    conf_keyword = 'range'
    def __init__(self, **kwargs):
        self.start = kwargs.get('start')
        self.end = kwargs.get('end')
        super(RangeConf, self).__init__(**kwargs)
    def parse_start_line(self, line):
        line = line.strip().strip(';').split(' ')
        print 'rangeline - %s' % (line)
        self.start = line[1]
        self.end = line[2]
    def serialize(self):
        return {'start':self.start, 'end':self.end}
    def __str__(self):
        return 'range: %s - %s' % (self.start, self.end)
        
def parse_conf(**kwargs):
    to_parse = kwargs.get('to_parse')
    filename = kwargs.get('filename')
    if to_parse is None:
        with open(filename, 'r') as f:
            to_parse = f.read()
    if isinstance(to_parse, basestring):
        to_parse = to_parse.splitlines()
    line_num = 0
    parsed_sects = []
    while line_num < len(to_parse):
        pkwargs = {'conf_lines':to_parse}
        if line_num != 0:
            pkwargs['start_line_num'] = line_num
        parsed_sect = ParsedSection(**pkwargs)
        if parsed_sect.end_line_num is None:
            break
        parsed_sects.append(parsed_sect)
        line_num = parsed_sect.end_line_num + 1
    networks = []
    for parsed_sect in parsed_sects:
        if 'shared-network' in parsed_sect.start_line:
            nobj = NetworkConf._parse(parsed_section=parsed_sect)
        elif 'subnet' in parsed_sect.start_line:
            sobj = SubnetConf._parse(parsed_section=parsed_sect)
            nobj = sobj.parent
        else:
            nobj = None
        if nobj is not None:
            networks.append(nobj)
    return networks
    
def parse_dt(dtstr):
    fmt_str = '%w %Y/%m/%d %H:%M:%S'
    if dtstr == 'never':
        return None
    return datetime.datetime.strptime(dtstr, fmt_str)
    
class LeaseConf(object):
    _conf_attrs = ['address', 'start_time', 'end_time', 
                   'binding_state', 'mac_address', 'uid']
    def __init__(self, **kwargs):
        self.address = kwargs.get('address')
        self.start_time = kwargs.get('start_time')
        self.end_time = kwargs.get('end_time')
        self.binding_state = kwargs.get('binding_state')
        self.mac_address = kwargs.get('mac_address')
        self.uid = kwargs.get('uid')
    @classmethod
    def _parse(cls, to_parse, **kwargs):
        if isinstance(to_parse, basestring):
            to_parse = to_parse.splitlines();
        new_kwargs = kwargs.copy()
        parse_dict = dict(zip([line.strip().split(' ')[0] for line in to_parse], 
                              [line.strip().rstrip(';').split(' ')[1:] for line in to_parse]))
        new_kwargs['address'] = parse_dict['lease'][0]
        new_kwargs['start_time'] = parse_dt(' '.join(parse_dict['starts']))
        new_kwargs['end_time'] = parse_dt(' '.join(parse_dict['ends']))
        new_kwargs['binding_state'] = parse_dict['binding'][1]
        new_kwargs['mac_address'] = parse_dict.get('hardware', [None, None])[1]
        new_kwargs['uid'] = parse_dict.get('uid', [None])[0]
        return cls(**new_kwargs)
    
def parse_leases(**kwargs):
    to_parse = kwargs.get('to_parse')
    filename = kwargs.get('filename')
    if to_parse is None:
        with open(filename, 'r') as f:
            to_parse = f.read()
    if isinstance(to_parse, basestring):
        to_parse = to_parse.splitlines()
    def iter_lines(start):
        for i in range(start, len(to_parse)):
            yield i, to_parse[i]
    def find_lease_lines(start_line=None):
        if start_line is None:
            start_line = 0
        lease_lines = None
        for i, line in iter_lines(start_line):
            if 'lease' in line and '{' in line:
                lease_lines = []
                lease_lines.append(line)
            elif '}' in line:
                if lease_lines is not None:
                    yield lease_lines
                lease_lines = None
            elif lease_lines is not None:
                lease_lines.append(line)
    leases = []
    for lines in find_lease_lines():
        obj = LeaseConf._parse(lines)
        leases.append(obj)
    return leases
