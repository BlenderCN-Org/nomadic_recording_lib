import array
from BaseObject import BaseObject
import incrementor

class LTCGenerator(BaseObject):
    def __init__(self, **kwargs):
        self.framerate = kwargs.get('framerate', 29.97)
        self.samplerate = kwargs.get('samplerate', 48000)
        if type(self.framerate) == float:
            cls = DropFrame
        else:
            cls = NonDropFrame
        self.frame_obj = cls(framerate=self.framerate)
        self.datablock = LTCDataBlock(framerate=self.framerate, frame_obj=self.frame_obj)
        
    def build_datablock(self, **kwargs):
        pass
        
class DropFrame(incrementor.Incrementor):
    def __init__(self, **kwargs):
        fr = kwargs.get('framerate', 29.97)
        res = int(round(fr))
        self.drop_period = int((res - fr) * 100)
        self.drop_count = 0
        self.framerate = fr
        kwargs['resolution'] = res
        kwargs['name'] = 'frame'
        super(DropFrame, self).__init__(**kwargs)
        self.add_child('second', incrementor.Second)
        self.bind(bounds_reached=self._on_own_bounds_reached)
        
    def _on_own_bounds_reached(self, **kwargs):
        if self.drop_count == self.drop_period - 1:
            self.resolution = self.resolution - 1
            self.drop_count = 0
        else:
            self.drop_count += 1
    
class NonDropFrame(incrementor.Incrementor):
    def __init__(self, **kwargs):
        fr = kwargs.get('framerate', 30)
        kwargs['resolution'] = fr
        kwargs['name'] = 'frame'
        super(NonDropFrame, self).__init__(**kwargs)
        self.add_child('second', incrementor.Second)
        
        
class LTCDataBlock(object):
    def __init__(self, **kwargs):
        self.framerate = kwargs.get('framerate')
        self.frame_obj = kwargs.get('frame_obj')
        self.all_frame_obj = self.frame_obj.get_all_obj()
        self.fields = {}
        self.fields_by_name = {}
        for key, cls in FIELD_CLASSES.iteritems():
            if type(key) == int:
                field = cls(parent=self)
                self.fields[key] = field
                self.fields_by_name[field.name] = field
            elif type(key) in [list, tuple]:
                for i, startbit in enumerate(key):
                    name = cls.__name__ + str(i)
                    field = cls(parent=self, start_bit=startbit, name=name)
                    self.fields[startbit] = field
                    self.fields_by_name[field.name] = field
                    
    @property
    def tc_data(self):
        fobj = self.all_frame_obj
        keys = fobj.keys()[:]
        return dict(zip(keys, [fobj[key].value for key in keys]))
        
    def build_data(self):
        i = 0
        l = []
        for bit, field in self.fields.iteritems():
            value = field.get_value()
            i += value << field.start_bit
            l.extend(field.get_list_value())
        s = bin(i)[2:]
        if s.count('0') % 2 == 1:
            i += 1 << self.fields['ParityBit'].start_bit
            l[self.Fields['ParityBit'].start_bit] = True
        return l
        
class Field(object):
    def __init__(self, **kwargs):
        self.parent = kwargs.get('parent')
        self.name = kwargs.get('name', self.__class__.__name__)
        if hasattr(self, '_start_bit'):
            self.start_bit = self._start_bit
        else:
            self.start_bit = kwargs.get('start_bit')
        if hasattr(self, '_bit_length'):
            self.bit_length = self._bit_length
        else:
            self.bit_length = 1
    def get_shifted_value(self):
        value = self.get_value()
        return value << self.start_bit
    def get_value(self):
        value = self.value_source()
        value = self.calc_value(value)
        return value
    def get_list_value(self):
        value = self.get_value()
        l = [bool(int(c)) for c in bin(value)[2:]]
        l.reverse()
        while len(l) < self.bit_length:
            l.append(False)
        return l
        
    def value_source(self):
        return 0
    def calc_value(self, value):
        return value

class FrameUnits(Field):
    _start_bit = 0
    _bit_length = 4
    def value_source(self):
        return self.parent.tc_data['frame']
    def calc_value(self, value):
        return value % 10
    
class FrameTens(Field):
    _start_bit = 8
    _bit_length = 2
    def value_source(self):
        return self.parent.tc_data['frame']
    def calc_value(self, value):
        return value / 10
    
class DropFlag(Field):
    _start_bit = 10
    def value_source(self):
        if type(self.parent.framerate) == float:
            return 1
        return 0
    
class ColorFlag(Field):
    _start_bit = 11
    
class SecondUnits(Field):
    _start_bit = 16
    _bit_length = 4
    def value_source(self):
        return self.parent.tc_data['second']
    def calc_value(self, value):
        return value % 10
    
class SecondTens(Field):
    _start_bit = 24
    _bit_length = 3
    def value_source(self):
        return self.parent.tc_data['second']
    def calc_value(self, value):
        return value / 10
    
class ParityBit(Field):
    _start_bit = 27
    
class MinuteUnits(Field):
    _start_bit = 32
    _bit_length = 4
    def value_source(self):
        return self.parent.tc_data['minute']
    def calc_value(self, value):
        return value % 10
    
class MinuteTens(Field):
    _start_bit = 40
    _bit_length = 3
    def value_source(self):
        return self.parent.tc_data['minute']
    def calc_value(self, value):
        return value / 10
    
class BinaryGroupFlag(Field):
    _start_bits = (43, 59)
    
class HourUnits(Field):
    _start_bit = 48
    _bit_length = 4
    def value_source(self):
        return self.parent.tc_data['hour']
    def calc_value(self, value):
        return value % 10
    
class HourTens(Field):
    _start_bit = 56
    _bit_length = 2
    def value_source(self):
        return self.parent.tc_data['hour']
    def calc_value(self, value):
        return value / 10
    
class Reserved(Field):
    _start_bit = 58
    
class SyncWord(Field):
    _start_bit = 64
    _bit_length = 16
    def value_source(self):
        return 0x3FFD
    
class UBits(Field):
    _bit_length = 4
    _start_bits = (4, 12, 20, 28, 36, 44, 52, 60)
    
def _GET_FIELD_CLASSES():
    d = {}
    for key, val in globals().iteritems():
        if type(val) != type:
            continue
        if issubclass(val, Field) and val != Field:
            if hasattr(val, '_start_bit'):
                dkey = val._start_bit
            elif hasattr(val, '_start_bits'):
                dkey = val._start_bits
            else:
                dkey = key
            d[dkey] = val
    return d
    
FIELD_CLASSES = _GET_FIELD_CLASSES()

if __name__ == '__main__':
    tcgen = LTCGenerator()
    d = tcgen.frame_obj.get_all_obj()
    d['minute'].value = 1
    d['hour'].value = 2
    d['second'].value = 40
    d['frame'].value = 19
    print tcgen.datablock.build_data()
    bob
