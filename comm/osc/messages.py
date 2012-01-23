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
        self.client = kwargs.get('client')
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
        return StringArgument(',' + ''.join([arg._type_tag for arg in self.arguments]))
        
    def add_argument(self, arg):
        if not getattr(arg, '_OSC_ARGUMENT_INSTANCE', False):
            arg = build_argument(obj=arg)
        self.arguments.append(arg)
        
    def parse_data(self, data):
        address, data = _strip_padding(data)
        tags, data = _strip_padding(data)
        args = []
        for tag in tags[1:]:
            arg, data = build_argument(type_tag=tag, data=data)
            args.append(arg)
        return dict(address=address, args=args)
        
    def build_string(self):
        args = [self.address, self.type_tags]
        args.extend(self.arguments)
        return ''.join([arg.build_string() for arg in args])
    
class Bundle(object):
    def __init__(self, *args, **kwargs):
        data = kwargs.get('data')
        if data is not None:
            kwargs = self.parse_data(data)
        timetag = kwargs.get('timetag', -1)
        if not isinstance(timetag, TimetagArgument):
            timetag = TimetagArgument(timetag)
        self.client = kwargs.get('client')
        self.timetag = timetag
        self.elements = []
        if 'elements' in kwargs:
            args = kwargs['elements']
        for element in args:
            self.add_element(element)
    def parse_data(self, data):
        bundlestr, data = _strip_padding(data)
        timetag, data = TimetagArgument.from_binary(TimetagArgument, data)
        elements = []
        while len(data):
            size, data = IntArgument.from_binary(IntArgument, data)
            elemdata = data[:size]
            elements.append((size, elemdata))
            data = data[size:]
        return dict(timetag=timetag, elements=elements)
    def add_element(self, element):
        if type(element) in [Bundle, Message]:
            self.elements.append(element)
            return
        size, data = element
        realelement = parse_message(data, client=self.client)
        self.elements.append(realelement)
    def build_string(self):
        data = ''.join([StringArgument('#bundle').build_string(), self.timetag.build_string()])
        for elem in self.elements:
            elemdata = elem.build_string()
            data += IntArgument(len(elemdata)).build_string()
            data += elemdata
        return data

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
        stuct_fmt = getattr(self, '_struct_fmt', None)
        if stuct_fmt is not None:
            s = struct.pack(stuct_fmt, cls(self))
            #print type(self), s
            return s
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
    def blahbuild_string(self):
        length = math.ceil((len(self)+1) / 4.0) * 4
        s = struct.pack('>%ds' % (length), self)
        print self, length
        return s
    
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

class Address(StringArgument):
    def __init__(self, value):
        if type(value) in [list, tuple]:
            value = '/' + '/'.join([v for v in value])
        super(Address, self).__init__(value)
    @property
    def head(self):
        return self.split()[0]
    @property
    def tail(self):
        return self.split()[-1:][0]
    def split(self):
        l = super(Address, self).split('/')
        if not len(l) or l[0] == '':
            return l
        return l[1:]
    def append(self, other):
        if not isinstance(other, Address):
            other = Address(other)
        l = self.split() + other.split()
        return Address(l)
    def append_right(self, other):
        if not isinstance(other, Address):
            other = Address(other)
        l = other.split() + self.split()
        return Address(l)
    def pop(self):
        sp = self.split()
        if len(sp) < 2:
            return '', self
        return sp[0], Address(sp[1:])

def build_argument(**kwargs):
    type_tag = kwargs.get('type_tag')
    data = kwargs.get('data')
    obj = kwargs.get('obj')
    cls = None
    if 'type_tag' in kwargs:
        cls = ARG_CLS_BY_TYPE_TAG[type_tag]
    elif 'obj' in kwargs:
        if cls is None:
            cls = ARG_CLS_BY_PYTYPE.get(type(obj))
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
    
def parse_message(data, client=None):
    if not len(data):
        return
    if data[0] == '/':
        return Message(data=data, client=client)
    if data[0] == '#':
        return Bundle(data=data, client=client)
    
if __name__ == '__main__':
    msg = Message(128, 128., address='/blah/stuff')
    print msg.arguments
    print [type(arg) for arg in msg.arguments]
    print msg.build_string()
    msg2 = parse_message(msg.build_string())
    print msg2.arguments
    print [type(arg) for arg in msg2.arguments]
    print msg2.build_string()
    bundle = Bundle(msg, msg2)
    print '\n'
    print bundle.elements, len(bundle.build_string())
    bundle2 = parse_message(bundle.build_string())
    print bundle.elements, len(bundle.build_string())
