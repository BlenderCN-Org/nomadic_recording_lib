import struct
import types
import math

class Message(object):
    def __init__(self, *args, **kwargs):
        data = kwargs.get('data')
        if data is not None:
            kwargs = self.parse_data(data)
        if 'args' in kwargs:
            args = kwargs['args']
        self.address = kwargs.get('address')
        self.arguments = []
        for arg in args:
            self.add_argument(arg)
            
    @property
    def address(self):
        return self._address
    @address.setter
    def address(self, value):
        self._address = StringArgument(value)
    @property
    def type_tags(self):
        return StringArgument(',' + [arg._type_tag for arg in self.arguments])
        
    def add_argument(self, arg):
        if not getattr(arg, '_OSC_ARGUMENT_INSTANCE', False):
            arg = build_argument(obj=arg)
        self.arguments.append(arg)
        
    def parse_data(self, data):
        address, data = _strip_padding(data)
        tags, data = _strip_padding(data)
        for tag in tags:
            arg, data = build_argument(type_tag=tag, data=data)
            args.append(arg)
        return dict(address=address, args=args)
        
    def build_string(self):
        args = [self.address, self.type_tags]
        args.extend(self.arguments)
        return ''.join([arg.build_string() for arg in args])
    
class Bundle(Message):
    pass

class Argument(object):
    _OSC_ARGUMENT_INSTANCE = True
    @staticmethod
    def from_binary(cls, data, **kwargs):
        value, data = cls.parse_binary(cls, data, **kwargs)
        return cls(value), data
    @staticmethod
    def parse_binary(cls, data, **kwargs):
        struct_fmt = getattr(cls, '_struct_fmt', None)
        if struct_fmt is None:
            return None, data
        value = struct.unpack(struct_fmt, data[:4])[0]
        return value, data[4:]
    def build_string(self):
        cls = getattr(self, '_pytype', self.__class__.__bases__[0])
        stuct_fmt = getattr(self, '_stuct_fmt', None)
        if stuct_fmt is not None:
            return struct.pack(stuct_fmt, cls(self))
        return ''
    
class IntArgument(int, Argument):
    _type_tag = 'i'
    #_pytype = int
    _struct_fmt = '>i'
    
class FloatArgument(float, Argument):
    _type_tag = 'f'
    #_pytype = float
    _struct_fmt = '>f'
    
class StringArgument(str, Argument):
    _type_tag = 's'
    #_pytype = str
    #_struct_fmt = 's'
    @property
    def _struct_fmt(self):
        length = math.ceil((len(self)+1) / 4.0) * 4
        return '>%ds' % (length)
    @staticmethod
    def parse_binary(cls, data, **kwargs):
        return _strip_padding(data)
    
class BlobArgument(list, Argument):
    _type_tag = 'b'
    
class BoolArgument(Argument):
    _pytype = bool
    def __init__(self, value):
        self._value = value
    @property
    def _type_tag(self):
        if self._value:
            return 'T'
        else:
            return 'F'
    @staticmethod
    def parse_binary(cls, data, **kwargs):
        tag = kwargs.get('type_tag')
        return tag == 'T', data
    
class NoneArgument(Argument):
    _type_tag = 'N'
    _pytype = types.NoneType
    
class TimetagPyType(float):
    pass
    
class TimetagArgument(TimetagPyType, Argument):
    _type_tag = 't'
    def build_string(self):
        if self < 0:
            return struct.pack('>qq', 0, 1)
        fr, sec = math.modf(self)
        return struct.pack('>qq', long(sec), long(fr * 1e9))
    @staticmethod
    def parse_binary(cls, data):
        binary = data[0:8]
        if len(binary) != 8:
            return False
            #raise OscError("Too few bytes left to get a timetag from %s." % (data))
        leftover = data[8:]
        if binary == '\0\0\0\0\0\0\0\1':
            # immediately
            time = -1.
        else:
            high, low = struct.unpack(">ll", data[0:8])
            time = float(int(high) + low / float(1e9))
        return time, leftover

ARG_CLASSES = (IntArgument, FloatArgument, StringArgument, BlobArgument, 
               BoolArgument, NoneArgument, TimetagArgument)
ARG_CLS_BY_PYTYPE = {}
ARG_CLS_BY_TYPE_TAG = {}
for argcls in ARG_CLASSES:
    if hasattr(argcls, '_pytype'):
        pytype = argcls._pytype
    else:
        pytype = argcls.__bases__[0]
    ARG_CLS_BY_PYTYPE[pytype] = argcls
    if hasattr(argcls, '_type_tag'):
        ARG_CLS_BY_TYPE_TAG[argcls._type_tag] = argcls
ARG_CLS_BY_PYTYPE[True] = BoolArgument
ARG_CLS_BY_PYTYPE[False] = BoolArgument
ARG_CLS_BY_PYTYPE[None] = NoneArgument

def build_argument(**kwargs):
    type_tag = kwargs.get('type_tag')
    data = kwargs.get('data')
    obj = kwargs.get('obj')
    cls = None
    if 'type_tag' in kwargs:
        cls = ARG_CLS_BY_TYPE_TAG[type_tag]
    elif 'obj' in kwargs:
        if cls is None:
            cls = ARG_CLS_BY_PYTYPE(type(obj))
        if cls is None:
            return False
        return cls(obj)
    else:
        return False
    arg, data = cls.from_binary(cls, data, type_tag=type_tag)
    return (arg, data)
    

def _find_pad_length(i):
    return i + (4 - (i % 4))
    
def _strip_padding(data):
    first_null = data.find('\0')
    padlen = _find_pad_length(first_null)
    return data[0:first_null], data[padlen:]
    
def parse_message(data):
    if not len(data):
        return
    if data[0] == '/':
        return Message(data=data)
    if data[0] == '#':
        return Bundle(data=data)
    