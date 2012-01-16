import array

from BaseObject import BaseObject
import incrementor

def biphase_encode(data, num_samples, max_value):
    samples_per_period = num_samples / len(data) / 4
    min_value = max_value * -1
    a = array.array('h')
    for value in data:
        if value:
            l = [max_value, min_value, max_value, min_value]
        else:
            l = [max_value, max_value, min_value, min_value]
        for v in l:
            a.extend([v] * samples_per_period)
    return a
    

class LTCGenerator(BaseObject):
    def __init__(self, **kwargs):
        self.framerate = kwargs.get('framerate', 29.97)
        self.samplerate = kwargs.get('samplerate', 48000)
        self.bitdepth = kwargs.get('bitdepth', 16)
        self.max_sampleval = 1 << (self.bitdepth - 2)
        self.samples_per_frame = self.samplerate / int(round(self.framerate))
        if type(self.framerate) == float:
            cls = DropFrame
        else:
            cls = NonDropFrame
        self.frame_obj = cls(framerate=self.framerate)
        self.datablock = LTCDataBlock(framerate=self.framerate, frame_obj=self.frame_obj)
        
    def build_datablock(self, **kwargs):
        return self.datablock.build_data()
        
    def build_audio_data(self, **kwargs):
        data = self.build_datablock()
        a = biphase_encode(data, self.samples_per_frame, self.max_sampleval)
        return a
        
class DropFrame(incrementor.Incrementor):
    def __init__(self, **kwargs):
        fr = kwargs.get('framerate', 29.97)
        res = int(round(fr))
        self.drop_period = int((res - fr) * 100)
        self.drop_count = 0
        self.framerate = fr
        self._enable_drop = False
        kwargs['resolution'] = res
        kwargs['name'] = 'frame'
        super(DropFrame, self).__init__(**kwargs)
        self.add_child('second', DropFrameSecond)
        
    @property
    def enable_drop(self):
        return self._enable_drop
    @enable_drop.setter
    def enable_drop(self, value):
        if value == self.enable_drop:
            return
        self._enable_drop = value
        print 'enable_drop: ', value
        
    def _on_value_set(self, **kwargs):
        if not self.enable_drop:
            return
        value = kwargs.get('value')
        if value in [0, 1]:
            self.value = 2
        
class DropFrameSecond(incrementor.Second):
    def __init__(self, **kwargs):
        super(DropFrameSecond, self).__init__(**kwargs)
        self.children['minute'].bind(value=self._on_minute_value_set)
    def check_for_drop(self):
        if self.children['minute'].value % 10 != 0:
            self.parent.enable_drop = True
        else:
            self.parent.enable_drop = False
    def _on_value_set(self, **kwargs):
        self.check_for_drop()
    def _on_minute_value_set(self, **kwargs):
        self.check_for_drop()
    
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
    import time
    tcgen = LTCGenerator()
    d = tcgen.frame_obj.get_all_obj()
    #d['minute'].value = 1
    #d['hour'].value = 2
    d['second'].value = 58
    d['frame'].value = 28
    keys = ['hour', 'minute', 'second', 'frame']
    values = tcgen.frame_obj.get_values()
    print ':'.join(['%02d' % (values[key]) for key in keys])
    for i in range(61):
        tcgen.frame_obj += 1
        values = tcgen.frame_obj.get_values()
        print ':'.join(['%02d' % (values[key]) for key in keys]), '   ', i
    a = tcgen.build_audio_data()
    print a
    
