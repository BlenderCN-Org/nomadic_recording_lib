
class ParseError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)
        
class ParsedVar(object):
    def __init__(self, name, other=None):
        self.name = name
        self.child_var = None
        if other:
            self.child_var = self.parse(other)
    @classmethod
    def parse(cls, parse_str, other=None):
        name = parse_str
        if '.' in parse_str:
            name = parse_str.split('.')[0]
            other = '.'.join(parse_str.split('.')[1:])
        return cls(name, other)
    def get_parsed(self):
        if self.child_var is not None:
            return {self.name:self.child_var.get_parsed()}
        return self.name
    def get_parsed_query_str(self):
        s = self.name
        if self.child_var is not None:
            s = '__'.join([s, self.child_var.get_parsed_query_str()])
        return s
        
class ParsedObject(object):
    def __init__(self, **kwargs):
        self.template = kwargs.get('template')
        self.start_index = kwargs.get('start_index')
        self.end_index = kwargs.get('end_index')
        self.parsed_var = self.build_parsed_var()
        print kwargs
        print '[%s]' % (self.template_chunk)
    @classmethod
    def parse(cls, **kwargs):
        template = kwargs.get('template')
        start = kwargs.get('start_index')
        end = None
        new_cls = None
        chunk = template.template_string[start:]
        if len(chunk) >= 2 and chunk[:3] == '{{ ':
            if ' }}' not in chunk:
                raise ParseError('no end tag found')
            new_cls = TaggedObject
            end = chunk.index(' }}') + 2 + start
        else:
            new_cls = UnTaggedObject
            if '{{ ' in chunk:
                end = chunk.find('{{ ') + start - 1
            else:
                end = len(template.template_string) - 1
        if new_cls is None or end is None:
            raise ParseError('could not figure stuff out')
        new_kwargs = dict(template=template, start_index=start, end_index=end)
        return new_cls(**new_kwargs)
    @property
    def template_chunk(self):
        tmp_str = self.template.template_string
        if not tmp_str:
            return None
        return tmp_str[self.start_index:self.end_index+1]
    def build_parsed_var(self):
        return None
    def get_parsed_var(self):
        if isinstance(self.parsed_var, ParsedVar):
            return self.parsed_var.get_parsed()
        return None
        
class UnTaggedObject(ParsedObject):
    pass
    
class TaggedObject(ParsedObject):
    def __init__(self, **kwargs):
        super(TaggedObject, self).__init__(**kwargs)
        
    def build_parsed_var(self):
        chunk = self.template_chunk
        chunk = chunk.lstrip('{{ ').rstrip(' }}')
        return ParsedVar.parse(chunk)
        
class Template(object):
    def __init__(self, template_str=None, **kwargs):
        self._template_string = None
        self.parsed_objects = {}
        self.template_string = template_str
    @property
    def template_string(self):
        return self._template_string
    @template_string.setter
    def template_string(self, value):
        if value == self._template_string:
            return
        self._template_string = value
        self.parse_template()
    def parse_template(self):
        self.parsed_objects.clear()
        tmp_str = self.template_string
        i = 0
        while i <= len(tmp_str) - 1:
            print i
            obj = ParsedObject.parse(template=self, start_index=i)
            #if obj.start_index in self.parsed_objects:
            #    break
            self.parsed_objects[obj.start_index] = obj
            i = obj.end_index + 1
    def get_parsed_vars(self):
        d = {'single':set(), 'complex':[]}
        for i, obj in self.parsed_objects.iteritems():
            v = obj.parsed_var
            vdata = obj.get_parsed_var()
            if vdata is None:
                continue
            if isinstance(vdata, basestring):
                d['single'].add(vdata)
            else:
                d['single'].add(v.name)
                d['complex'].append(vdata)
        return d

class ValueObject(object):
    def __init__(self, **kwargs):
        self.start_index = None
        self.end_index = None
        self.parser = kwargs.get('parser')
        self.parsed_object = kwargs.get('parsed_object')
    @classmethod
    def new(cls, **kwargs):
        obj = kwargs.get('parsed_object')
        new_cls = UnTaggedValueObject
        if isinstance(obj, TaggedObject):
            new_cls = TaggedValueObject
        return new_cls(**kwargs)
    def get_chunk(self):
        s = self.parser.string_to_parse
        start = self.start_index
        end = self.end_index
        if end is None:
            end = len(s) - 1
        return s[start:end+1]
    def get_parsed_value(self):
        return self.parsed_object.parsed_var, self.get_chunk()
    def calc_indecies(self):
        last_key, next_key = self.get_neighbor_keys()
        start = self.start_index = self.calc_start_index(last_key, next_key)
        end = self.end_index = self.calc_end_index(last_key, next_key)
        if last_key is not None and start is None:
            return False
        if next_key is not None and end is None:
            return False
        return True
    def calc_start_index(self, last_key, next_key):
        if last_key is None:
            return 0
        last_obj = self.parser.value_objects[last_key]
        return last_obj.end_index + 1
    def get_neighbor_keys(self):
        start = self.parsed_object.start_index
        all_keys = sorted(self.parser.value_objects.keys())
        i = all_keys.index(start)
        if i == 0:
            last_key = None
        else:
            last_key = all_keys[i-1]
        if i >= len(all_keys):
            next_key = None
        else:
            next_key = all_keys[i+1]
        return last_key, next_key
        
class UnTaggedValueObject(ValueObject):
    def calc_end_index(self, last_key, next_key):
        if next_key is None:
            return None
        pobj = self.parsed_object
        return self.start_index + (pobj.end_index - pobj.start_index)
class TaggedValueObject(ValueObject):
    def calc_end_index(self, last_key, next_key):
        if next_key is None:
            return None
        next_obj = self.parser.value_objects[next_key]
        if next_obj.start_index is None:
            return None
        return next_obj.start_index - 1
    
        
class TemplatedStringParser(object):
    def __init__(self, **kwargs):
        self.value_objects = {}
        self.template = kwargs.get('template')
        self.string_to_parse = kwargs.get('string_to_parse')
        self.build_value_obj()
        r = self.calc_value_obj_indecies()
        self.success = r
    def build_value_obj(self):
        parsed_objects = self.template.parsed_objects
        value_objects = self.value_objects
        last_vobj = None
        for i in sorted(parsed_objects.keys()):
            pobj = parsed_objects[i]
            vobj = ValueObject.new(parser=self, parsed_object=pobj)
            value_objects[i] = vobj
    def calc_value_obj_indecies(self):
        value_objects = self.value_objects
        keys = sorted(value_objects.keys())
        loop_max = 10
        i = 0
        while i <= loop_max:
            calc_complete = True
            for key in keys:
                r = value_objects[key].calc_indecies()
                if r is False:
                    calc_complete = False
            if calc_complete:
                break
            i += 1
        return calc_complete
    def get_parsed_values(self):
        d = {}
        for i, vobj in self.value_objects.iteritems():
            if isinstance(vobj, UnTaggedValueObject):
                continue
            pvar, pval = vobj.get_parsed_value()
            qstr = pvar.get_parsed_query_str()
            if qstr in d:
                if d[qstr] == pval:
                    continue
                raise ParseError('unmatched values for %s: [%s, %s]' % (qstr, d[qstr], pval))
            d[qstr] = pval
        return d
        
