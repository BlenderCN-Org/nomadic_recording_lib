
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

class TemplatedStringParser(object):
    def __init__(self, **kwargs):
        self.template = kwargs.get('template')
        self.string_to_parse = kwargs.get('string_to_parse')
        ## then do magic stuff with all the things above
