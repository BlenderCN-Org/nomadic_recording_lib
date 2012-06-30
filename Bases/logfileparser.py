from curses import ascii

from BaseObject import BaseObject


class BaseParser(BaseObject):
    _Properties = {'field_names':dict(default=[]), 
                   'key_field':dict(ignore_type=True)}
    def __init__(self, **kwargs):
        super(BaseParser, self).__init__(**kwargs)
        self.parsed = {}
        self.sorted = {}
        self.bind(field_names=self.on_field_names_set)
        field_names = kwargs.get('field_names')
        if field_names is not None:
            self.field_names.extend(field_names)
        self.key_field = kwargs.get('key_field')
        
    def do_sort(self, parsed):
        return {}
        
    def on_field_names_set(self, **kwargs):
        pass
        
class FileParser(BaseParser):
    _Properties = {'filename':dict(ignore_type=True), 
                   'rw_mode':dict(default='r')}
    def __init__(self, **kwargs):
        self.fileobj = None
        super(FileParser, self).__init__(**kwargs)
        rw_mode = kwargs.get('rw_mode')
        if rw_mode is not None:
            self.rw_mode = rw_mode
        self.bind(filename=self.on_filename_set)
        self.filename = kwargs.get('filename')
        
    def parse_file(self):
        print 'parse file', self.filename
        self.open_file()
        parsed = self.do_parse()
        #print parsed
        self.parsed.update(parsed)
        self.sorted.update(self.do_sort(parsed))
        self.close_file()
        
    def open_file(self):
        self.close_file()
        if self.filename is None:
            print 'file is none'
            return
        f = open(self.filename, self.rw_mode)
        self.fileobj = f
        print f
        
    def close_file(self, **kwargs):
        f = self.fileobj
        if f is None:
            return
        f.close()
        self.fileobj = None
        
    def do_parse(self):
        return {}
        
    def on_filename_set(self, **kwargs):
        print 'filename set', kwargs
        self.parse_file()
        

NON_CTRL_DELIMITERS = dict(comma=',', semicolon=';', colon=':', space=' ')

class DelimitedFileParser(FileParser):
    _Properties = {'field_names_in_header':dict(default=True), 
                   'header_line_num':dict(default=0), 
                   'line_strip_chars':dict(default=''), 
                   'delimiter':dict(default=',', fformat='_format_delimiter', ignore_type=True), 
                   'quote_char':dict(default=None, ignore_type=True)}
    def __init__(self, **kwargs):
        super(DelimitedFileParser, self).__init__(**kwargs)
        for key in ['header_line_num', 'line_strip_chars', 'delimiter', 'quote_char']:
            val = kwargs.get(key)
            if val is not None:
                print 'setattr: ', key, val
                setattr(self, key, val)
            
    def do_parse(self):
        f = self.fileobj
        if f is None:
            return
        delim = self.delimiter
        quote_char = self.quote_char
        is_quoted = quote_char is not None
        field_names = self.field_names
        line_strip_chars = self.line_strip_chars
        header_line_num = self.header_line_num
        def parse_line(s):
            l = []
            s = s.lstrip(line_strip_chars)
            if delim != ' ':
                s = s.strip()
            for field in s.split(delim):
                if is_quoted:
                    if field[:1] == quote_char and field[-1:] == quote_char:
                        field = field[1:-1]
                    else:
                        if field.isdigit():
                            field = int(field)
                        elif '.' in field and False not in [n.isdigit() for n in field.split('.')]:
                            field = float(field)
                l.append(field)
            return l
        d = {'pre_header':[], 'fields_by_line':{}, 'fields_by_key':{}}
        i = 0
        line_num = 0
        for line in f:
            if i < header_line_num:
                d['pre_header'].append(line)
                i += 1
                line_num += 1
                continue
            if i == header_line_num:
                if self.field_names_in_header:
                    field_names = parse_line(line)
                    ##self.field_names = field_names
                    for fn in field_names:
                        d['fields_by_key'][fn] = {}
                    line_num = 0
                    i += 1
                    continue
            if line.startswith('#'):
                i += 1
                continue
            parsed = parse_line(line)
            d['fields_by_line'][line_num] = {}
            for field_index, field_val in enumerate(parsed):
                field_name = field_names[field_index]
                d['fields_by_key'][field_name][line_num] = field_val
                d['fields_by_line'][line_num][field_name] = field_val
                #d['fields'][field_names[field_index]][line_num] = field_val
            i += 1
            line_num += 1
        return d
        
    def on_field_names_set(self, **kwargs):
        pass
        
    def _format_delimiter(self, value):
        print 'format_delim: ', value
        if type(value) in [str, unicode]:
            print 'delim is str type'
            if value.upper() in dir(ascii):
                i = getattr(ascii, value.upper())
                print 'ord is ', i, ', chr is ', chr(i)
                return chr(i)
            if value.lower() in NON_CTRL_DELIMITERS:
                return NON_CTRL_DELIMITERS[value.lower()]
        return value
