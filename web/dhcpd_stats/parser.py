import datetime

PARSED_NETWORKS = []
PARSED_LEASES = []

class BracketLocation(object):
    def __init__(self, line, col):
        self.line = line
        self.col = col
    def __cmp__(self, other):
        if not isinstance(other, BracketLocation):
            other = BracketLocation(*other)
        if self.line < other.line:
            return -1
        if self.line > other.line:
            return 1
        if self.col < other.col:
            return -1
        if self.col > other.col:
            return 1
        return 0
    def __str__(self):
        return 'line %02d, col %02d' % (self.line, self.col)
class OpenBracket(BracketLocation):
    def __repr__(self):
        return '%s {' % (self)
class CloseBracket(BracketLocation):
    def __repr__(self):
        return '%s }' % (self)
class Text(str):
    @property
    def lines(self):
        v = getattr(self, '_lines', None)
        if v is None:
            v = self._lines = self.splitlines()
        return v
    def iter_bracket_content(self, start, end=None):
        lines = self.lines
        if end is None:
            end = CloseBracket(len(lines)-1, len(lines[-1])-1)
        start_line = start.line
        if isinstance(start, CloseBracket):
            start_line += 1
        end_line = end.line
        if isinstance(end, OpenBracket):
            end_line -= 1
        for i in range(start_line, end_line+1):
            yield i, lines[i]
            
class BracketedEnclosure(object):
    def __init__(self, **kwargs):
        self.parent = kwargs.get('parent')
        self._text = kwargs.get('text')
        start = kwargs.get('start')
        if not isinstance(start, OpenBracket) and start is not None:
            start = OpenBracket(*start)
        self.start = start
        end = kwargs.get('end')
        if not isinstance(end, CloseBracket) and end is not None:
            end = CloseBracket(*end)
        self.end = end
        self.children = []
        if self.start is None:
            self.find_start()
        if self.end is None:
            self.find_end()
        self.find_children()
    @property
    def text(self):
        t = self._text
        if t is None:
            t = self.parent.text
        return t
    def find_start(self):
        if self.parent is not None:
            pstart = self.parent.end
        else:
            pstart = BracketLocation(0, 0)
        for i, line in self.text.iter_bracket_content(pstart):
            if '{' not in line:
                continue
            self.start = OpenBracket(i, line.index('{'))
            break
    def find_end(self):
        if self.parent is not None:
            pend = self.parent.end
        else:
            pend = None
        #for i, line in self.text.iter_bracket_content(self.start, pend):
        #    if '}' in line:
    def find_children(self):
        pass
        
        
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
    @property
    def all_text(self):
        return '\n'.join([line for i, line in self.iter_lines()])
    @property
    def text_with_line_num(self):
        return '\n'.join(['%03d - %s' % (i, line) for i, line in self.iter_lines()])
    def iter_children(self):
        for i in sorted(self.child_sections.keys()):
            yield self.child_sections[i]
    def search_brackets(self):
        open_brackets = 0
        bracket_found = False
        def add_child(line_num):
            if line_num in self.child_sections.keys():
                return
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
        for i in range(start_line, end_line+1):
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
    def get_ranges(self):
        for subnet in self.subnets.itervalues():
            for r in subnet.get_ranges():
                yield r
    def serialize(self):
        d = {'name':self.name, 'subnets':{}}
        for k, v in self.subnets.iteritems():
            d['subnets'][k] = v.serialize()
        return d
    def __repr__(self):
        return 'NetworkConf: %s' % (self)
    def __str__(self):
        return self.name
    
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
        #print self.parsed_section.serialize()
        for p in self.parse_children(PoolConf):
            self.pools.append(p)
    def parse_start_line(self, line):
        line = line.split(' ')
        self.address = line[1]
        self.netmask = line[3]
    def get_ranges(self):
        for p in self.pools:
            for r in p.ranges:
                yield r
    def serialize(self):
        d = {'address':self.address, 'netmask':self.netmask, 'pools':[]}
        for v in self.pools:
            d['pools'].append(v.serialize())
        return d
    def __repr__(self):
        return 'SubnetConf: %s' % (self)
    def __str__(self):
        return self.address
    
class PoolConf(ParseBase):
    conf_keyword = 'pool'
    def __init__(self, **kwargs):
        self.ranges = []
        super(PoolConf, self).__init__(**kwargs)
        #print '---------------'
        #print '\n'.join([t[1] for t in self.parsed_section.iter_lines()])
    def parse_start_line(self, line):
        ## TODO: find out why multiple pools aren't being parsed
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
        self.id = str(self)
        super(RangeConf, self).__init__(**kwargs)
    def parse_start_line(self, line):
        line = line.strip().strip(';').split(' ')
        self.start = line[1]
        self.end = line[2]
    def serialize(self):
        return {'start':self.start, 'end':self.end}
    def __repr__(self):
        return 'RangeConf: %s' % (self)
    def __str__(self):
        return '%s - %s' % (self.start, self.end)
        
def parse_conf(**kwargs):
    global PARSED_NETWORKS
    to_parse = kwargs.get('to_parse')
    filename = kwargs.get('filename')
    return_parsed = kwargs.get('return_parsed')
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
    for parsed_sect in parsed_sects:
        if 'shared-network' in parsed_sect.start_line:
            nobj = NetworkConf._parse(parsed_section=parsed_sect)
        elif 'subnet' in parsed_sect.start_line:
            sobj = SubnetConf._parse(parsed_section=parsed_sect)
            nobj = sobj.parent
        else:
            nobj = None
        if nobj is not None:
            PARSED_NETWORKS.append(nobj)
    if return_parsed:
        return PARSED_NETWORKS, parsed_sects
    return PARSED_NETWORKS
    
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
    def __repr__(self):
        return '%s: %s' % (self.__class__.__name__, self)
    def __str__(self):
        return str(self.address)
    
def parse_leases(**kwargs):
    global PARSED_LEASES
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
    for lines in find_lease_lines():
        obj = LeaseConf._parse(lines)
        PARSED_LEASES.append(obj)
    return PARSED_LEASES
