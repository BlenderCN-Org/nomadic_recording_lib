
class Message(object):
    pass
    
class Bundle(Message):
    pass

class Argument(object):
    pass
    
class IntArgument(Argument):
    _type_tag = 'i'
    _pytype = int
    
class FloatArgument(Argument):
    _type_tag = 'f'
    _pytype = float
    
class StringArgument(Argument):
    _type_tag = 's'
    _pytype = str
    
class BlobArgument(Argument):
    _type_tag = 'b'
    
class BoolArgument(Argument):
    pass
    
class NoneArgument(Argument):
    _type_tag = 'N'
    
class TimetagArgument(Argument):
    _type_tag = 't'
    _pytype = float
