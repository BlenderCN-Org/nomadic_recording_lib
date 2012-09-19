import os.path
from curses import ascii

from BaseObject import BaseObject

class LogEntry(object):
    def __init__(self, **kwargs):
        #super(LogEntry, self).__init__(**kwargs)
        self._field_names = kwargs.get('field_names')
        self.parser = kwargs.get('parser')
        self.id = kwargs.get('id')
        self.field_list = []
        self.fields = {}
        data = kwargs.get('data')
        self.data = data
        self.parse(data=data)
    @property
    def field_names(self):
        if self._field_names is not None:
            return self._field_names
        return self.parser.field_names
    def parse(self, **kwargs):
        pass
    def get_dict(self):
        keys = ['id', 'field_names', 'fields']
        d = dict(zip(keys, [getattr(self, key) for key in keys]))
        return d
    
class DelimitedLogEntry(LogEntry):
    def __init__(self, **kwargs):
        super(DelimitedLogEntry, self).__init__(**kwargs)
        
    def parse(self, **kwargs):
        data = kwargs.get('data')
        parser = self.parser
        delim = parser.delimiter
        field_names = self.field_names
        field_list = self.field_list
        parse_field = self.parse_field
        #s = s.lstrip(self.line_strip_chars)
        if delim != ' ':
            data = data.strip()
        for field in data.split(delim):
            field_list.append(parse_field(field))
        if field_names is not None:
            self.fields.update(dict(zip(field_names, field_list)))
            
    def parse_field(self, field):
        quote_char = self.parser.quote_char
        if quote_char is None:
            return field
        if field[:1] == quote_char and field[-1:] == quote_char:
            field = field[1:-1]
        else:
            if field.isdigit():
                field = int(field)
            elif '.' in field and False not in [n.isdigit() for n in field.split('.')]:
                field = float(field)
        return field

class BaseParser(BaseObject):
    _Properties = {'field_names':dict(default=[]), 
                   'key_field':dict(ignore_type=True)}
    def __init__(self, **kwargs):
        super(BaseParser, self).__init__(**kwargs)
        cls = kwargs.get('entry_class')
        if cls is not None:
            self.entry_class = cls
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
        
    def build_entry(self, **kwargs):
        kwargs['parser'] = self
        return self.entry_class(**kwargs)
        
    def get_dict(self):
        entries = self.parsed
        keys = entries.keys()
        d = {'entries':dict(zip(keys, [entries[key].get_dict() for key in keys]))}
        return d
        
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
        
    def parse_file(self, **kwargs):
        f = self.open_file(**kwargs)
        parsed = self.do_parse(fileobj=f)
        #print parsed
        #self.parsed.update(parsed)
        for key, val in parsed.iteritems():
            d = self.parsed.get(key)
            if d is None:
                self.parsed[key] = val
            else:
                print 'updating: ', key, val
                d.update(val)
        self.sorted.update(self.do_sort(parsed))
        self.close_file(fileobj=f)
        
    def open_file(self, **kwargs):
        filename = kwargs.get('filename', self.filename)
        #self.close_file()
        if filename is None:
            print 'file is none'
            return
        f = open(filename, self.rw_mode)
        if self.fileobj is None:
            self.fileobj = f
        return f
        
    def close_file(self, **kwargs):
        f = kwargs.get('fileobj', self.fileobj)
        if f is None:
            return
        f.close()
        if f == self.fileobj:
            self.fileobj = None
        
    def do_parse(self, **kwargs):
        return {}
        
    def on_filename_set(self, **kwargs):
        value = kwargs.get('value')
        parse_file = self.parse_file
        if type(value) in [list, tuple]:
            for fn in value:
                parse_file(filename=fn)
        else:
            parse_file(filename=kwargs.get('value'))
    

NON_CTRL_DELIMITERS = dict(comma=',', semicolon=';', colon=':', space=' ')

class DelimitedFileParser(FileParser):
    _Properties = {'field_names_in_header':dict(default=True), 
                   'header_line_num':dict(default=0), 
                   'line_strip_chars':dict(default=''), 
                   'delimiter':dict(default=',', fformat='_format_delimiter', ignore_type=True), 
                   'quote_char':dict(default=None, ignore_type=True)}
    entry_class = DelimitedLogEntry
    def __init__(self, **kwargs):
        super(DelimitedFileParser, self).__init__(**kwargs)
        for key in ['header_line_num', 'line_strip_chars', 'delimiter', 'quote_char']:
            val = kwargs.get(key)
            if val is not None:
                print 'setattr: ', key, val
                setattr(self, key, val)
            
    def parse_line(self, s):
        quote_char = self.quote_char
        delim = self.delimiter
        parse_field = self.parse_field
        s = s.lstrip(self.line_strip_chars)
        if delim != ' ':
            s = s.strip()
        for field in s.split(delim):
            yield parse_field(field)
        
    def parse_field(self, field):
        quote_char = self.quote_char
        if quote_char is None:
            return field
        if field[:1] == quote_char and field[-1:] == quote_char:
            field = field[1:-1]
        else:
            if field.isdigit():
                field = int(field)
            elif '.' in field and False not in [n.isdigit() for n in field.split('.')]:
                field = float(field)
        return field
        
    def process_header(self, line_number, line):
        if line_number < self.header_line_num:
            return True, line
        return False, line
        
    def process_field_header(self, line_number, line):
        if line_number != self.header_line_num:
            return False
        if not self.field_names_in_header:
            return False
        entry = self.build_entry(data=line)
        return entry
        #l = []
        #for fn in self.parse_line(line):
        #    l.append(fn)
        #return True, l
        
    def do_parse(self, **kwargs):
        f = kwargs.get('fileobj', self.fileobj)
        if f is None:
            return
        delim = self.delimiter
        quote_char = self.quote_char
        is_quoted = quote_char is not None
        field_names = self.field_names
        current_field_names = field_names[:]
        line_strip_chars = self.line_strip_chars
        header_line_num = self.header_line_num
        parse_line = self.parse_line
        process_header = self.process_header
        process_field_header = self.process_field_header
        d = {'header_data':{}, 'entries':{}}
        i = 0
        line_num = 0
        for line in f:
            line = line.rstrip('\n').rstrip('\r')
            if not len(line):
                continue
            is_header, header_data = process_header(i, line)
            if is_header:
                d['header_data'][i] = header_data
                i += 1
                line_num += 1
                continue
            field_header = process_field_header(i, line)
            if field_header is not False:
                for fn in field_header.field_list:
                    if fn in field_names:
                        continue
                    #d['fields_by_key'][fn] = {}
                    field_names.append(fn)
                current_field_names = field_header.field_list[:]
                line_num -= 1
                i += 1
                continue
            if line.startswith('#'):
                i += 1
                continue
            entry = self.build_entry(data=line, id=line_num, field_names=current_field_names)
            d['entries'][entry.id] = entry
            #d['fields_by_line'][line_num] = {}
            #field_index = 0
            #for field_val in parse_line(line):
            #    field_name = field_names[field_index]
            #    d['fields_by_key'][field_name][line_num] = field_val
            #    d['fields_by_line'][line_num][field_name] = field_val
            #    field_index += 1
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

class W3CExtendedLogfileParser(DelimitedFileParser):
    def process_header(self, line_number, line):
        if line.startswith('#Fields:'):
            return False, line
        if not line.startswith('#'):
            return False, line
        line = line.strip('#')
        key, val = line.split(': ')
        return True, {key:val, 'line_number':line_number}
    def process_field_header(self, line_number, line):
        if len(self.field_names):
            return False
        if not line.startswith('#Fields:'):
            return False
        line = line.lstrip('#Fields:')
        return self.build_entry(data=line)
        #l = []
        #for fn in self.parse_line(line):
        #    l.append(fn)
        #return True, l

class W3CExtendedLogfileRollingParser(W3CExtendedLogfileParser):
    _Properties = {'last_line_number':dict(default=0)}
    def do_parse(self, **kwargs):
        parsed = super(W3CExtendedLogfileRollingParser, self).do_parse(**kwargs)
        last_line = max(parsed['fields_by_line'].keys())
        if self.last_line_number == 0:
            self.last_line_number = last_line
            print 'last_line:', last_line
            return parsed
        keys = parsed['fields_by_line'].keys()[:]
        for key in keys:
            newkey = key + last_line + 1
            val = parsed['fields_by_line'][key]
            del parsed['fields_by_line'][key]
            parsed['fields_by_line'][newkey] = val
        for fieldname, fields in parsed['fields_by_key'].iteritems():
            keys = fields.keys()[:]
            for key in keys:
                newkey = key + last_line + 1
                val = fields[key]
                del fields[key]
                fields[newkey] = val
        keys = parsed['header_data'].keys()[:]
        for key in keys:
            newkey = key + last_line + 1
            val = parsed['header_data'][key]
            del parsed['header_data'][key]
            parsed['header_data'][newkey] = val
        print parsed, last_line
        self.last_line_number = last_line
        return parsed
        
    def on_filename_set(self, **kwargs):
        prop = kwargs.get('Property')
        value = kwargs.get('value')
        if type(value) in [str, unicode]:
            filenames = []
            path = os.path.dirname(value)
            basefile = os.path.basename(value)
            for fn in os.listdir(path):
                if fn.startswith(basefile):
                    filenames.append(os.path.join(path, fn))
            prop.value = filenames
            kwargs['value'] = filenames
        super(W3CExtendedLogfileRollingParser, self).on_filename_set(**kwargs)
        
        
