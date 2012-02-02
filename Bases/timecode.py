import time
import array
import collections
import struct

from BaseObject import BaseObject
import incrementor

def biphase_encode(data, num_samples, max_value):
    samples_per_period = num_samples / len(data) / 4
    #print 'num_samp=%s, maxv=%s, s_per_period=%s' % (num_samples, max_value, samples_per_period)
    min_value = max_value * -1
    #a = array.array('h')
    a = []
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
        best_sr = kwargs.get('use_best_samplerate', False)
        if best_sr:
            fr = self.framerate
            #r, frac = divmod(fr, int(fr))
            r = int(fr)
            frac = fr % r
            sr = (r * 100) + int(round(frac * 100))
            while (sr / fr) / 80 < 16:
                sr *= 2
            self.samplerate = sr
            self.samples_per_frame = int(round(sr / fr))
            print 'samplerate=%s, s_per_frame=%s' % (self.samplerate, self.samples_per_frame)
        else:
            self.samplerate = kwargs.get('samplerate', 48000)
            self.samples_per_frame = int(round(self.samplerate / self.framerate))
        self.bitdepth = kwargs.get('bitdepth', 16)
        self.max_sampleval = 1 << (self.bitdepth - 2)
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
        #print 'enable_drop: ', value

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
            i += 1 << self.fields_by_name['ParityBit'].start_bit
            l[self.fields_by_name['ParityBit'].start_bit] = True
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

if False:#__name__ == '__main__':
    tcgen = LTCGenerator(use_best_samplerate=True)
    d = {'frame':10, 'second':5, 'minute':20, 'hour':2}
    tcgen.frame_obj.set_values(**d)
    print tcgen.frame_obj.get_values()
    data = tcgen.build_datablock()
    print len(data), data
    print tcgen.build_audio_data()
    
if __name__ == '__main__':
    import time
    import threading
    import datetime
    import gobject, glib
    import gst

    class A(object):
        def __init__(self):
            self.tcgen = LTCGenerator(use_best_samplerate=True)
            now = datetime.datetime.now()
            self.buffer_lock = threading.Lock()
            self.start = now
            d = {}
            for key in ['hour', 'minute', 'second']:
                d[key] = getattr(now, key)
            ms = float(now.microsecond) / (10 ** 6)
            if d['second'] == 0 and d['minute'] % 10 != 0:
                frame = int(round(ms / (1/28.)))
                frame += 2
            else:
                frame = int(round(ms / (1/30.)))
            if frame > 29:
                frame = 29
            d['frame'] = frame
            self.tcgen.frame_obj.set_values(**d)
            print 'start: ', self.tcgen.frame_obj.get_values(), now.strftime('%X.%f')
            self.last_timestamp = time.time()
            self.buffer = collections.deque()
            self.buffer.extend(self.tcgen.build_audio_data())
            #self.increment_and_build_data(150)
            #self.buffer.extend(self.tcgen.build_audio_data())
            #print len(self.buffer)
        def increment_and_build_data(self, count=1):
            tcgen = self.tcgen
            fr_obj = tcgen.frame_obj
            audbuffer = self.buffer
            buffer_lock = self.buffer_lock
            for i in range(count):
                fr_obj += 1
                abuf = tcgen.build_audio_data()
                #with buffer_lock:
                audbuffer.extend(abuf)
        def on_vident_handoff(self, ident, buffer):
            #now = time.time()
            #print now - self.last_timestamp
            #self.last_timestamp = now
            self.increment_and_build_data()
            #print self.tcgen.frame_obj.get_values()
            self.timestamp = buffer.timestamp
            self.asrc.emit('need-data', self.tcgen.samples_per_frame * 2)
            d = self.tcgen.frame_obj.get_values()
            self.toverlay.set_property('text', ':'.join(['%02i' % (d[key]) for key in ['hour', 'minute', 'second', 'frame']]))
            return (ident, buffer)
        
        def on_audneeddata(self, element, length):
            #ts = element.get_clock().get_time() - element.get_base_time()
            #audbuffer = self.buffer
#            print [e.get_caps().to_string() for e in element.src_pads()]
#            print element.get_property('caps')
#            print 'length needed: ', length
#            print 'abuffer len: ', len(audbuffer)
            #if len(audbuffer) < length / 4:
            #    return
            #with self.buffer_lock:
            tcbuf = self.get_samples_from_buffer(self.tcgen.samples_per_frame)
            if tcbuf is False:
                print 'BUFFER EMPTY!!!'
                element.emit('end-of-stream')
                return
            tcstr = tcbuf.tostring()
            buffer = gst.Buffer(tcstr)
            buffer.set_caps(element.get_property('caps'))
            buffer.timestamp = self.timestamp
            #print buffer.timestamp
            #buffer.timestamp = element.get_clock().get_time()
            #print 'buffer: ', len(tcstr)
            #print 'new abuffer len: ', len(audbuffer)
            element.emit('push-buffer', buffer)
        def get_samples_from_buffer(self, num_samples):
            buffer = self.buffer
            if len(buffer) < num_samples:
                return False
            out = array.array('h')
            for i in range(num_samples):
                out.append(buffer.popleft())
            return out
        def on_atestsrc_push(self, element, buffer):
            print 'atestsrcbuffer:\n', buffer
        def on_bus_message(self, bus, msg):
            print msg
    a = A()
    p = gst.Pipeline()
    bus = p.get_bus()
    bus.add_signal_watch()
    bus.connect('message', a.on_bus_message)
    vqueue = gst.element_factory_make('queue')
    vsrc = gst.element_factory_make('videotestsrc')
    vident = gst.element_factory_make('identity')
    toverlay = gst.element_factory_make('cairotextoverlay')
    a.toverlay = toverlay
    vcapf = gst.element_factory_make('capsfilter')
    vcaps = gst.Caps('video/x-raw-yuv, framerate=30000/1001')
    vcapf.set_property('caps', vcaps)
    vout = gst.element_factory_make('xvimagesink')
    vident.connect('handoff', a.on_vident_handoff)

    aqueue = gst.element_factory_make('queue')
    #asrc = gst.element_factory_make('audiotestsrc')
    #asrc.set_property('wave', 1)
    #asrc.set_property('samplesperbuffer', 800)
    #asrc.set_property('volume', 1.)
    
    asrc = gst.element_factory_make('appsrc')
    a.asrc = asrc
    asrc.set_do_timestamp(True)
    #asrc.set_property('size', 800)

    asrc.set_property('is-live', True)
    #asrc.set_property('size', 400)
    #asrc.set_property('max-bytes', a.tcgen.samples_per_frame / 2)
    #asrc.set_property('min-percent', 100)
    asrc.set_property('block', True)
    asrc.set_property('emit-signals', False)
    
    capsstr = 'audio/x-raw-int, rate=%s, channels=1, width=16, signed=true' % (a.tcgen.samplerate)
    asrccaps = gst.caps_from_string(capsstr)
    asrc.set_property('caps', asrccaps)
    #asrccapf = gst.element_factory_make('capsfilter')
    #asrccaps = gst.Caps()
    #asrccapf.set_property('caps', asrccaps)
    #asrc.set_property('caps', asrccaps)
    aident = gst.element_factory_make('identity')
    audrate = gst.element_factory_make('audioresample')
    audrate.set_property('quality', 10)
    audratecaps = gst.caps_from_string('audio/x-raw-int, rate=48000')
    audratecapf = gst.element_factory_make('capsfilter')
    audratecapf.set_property('caps', audratecaps)
    aenc = gst.element_factory_make('wavenc')
    aconv = gst.element_factory_make('audioconvert')
    #aout = gst.element_factory_make('fakesink')
    aout = gst.element_factory_make('filesink')
    aout.set_property('location', '/home/nocarrier/ltctest.wav')
    #aout = gst.element_factory_make('jackaudiosink')
    #aout = gst.element_factory_make('autoaudiosink')

    vidchain = [vsrc, vident, toverlay, vcapf, vout]
    for e in vidchain:
        p.add(e)
    audchain = [asrc, aident, audrate, audratecapf, aenc, aout]
    for e in audchain:
        p.add(e)
    gst.element_link_many(vsrc, vident, toverlay, vcapf, vout)
    gst.element_link_many(*audchain)
    asrc.connect('need-data', a.on_audneeddata)
    #aident.connect('handoff', a.on_aident_handoff)
    #asrc.connect('push-buffer', a.on_atestsrc_push)
    gobject.threads_init()
    p.set_state(gst.STATE_PLAYING)
    #time.sleep(5.)
    #p.set_state(gst.STATE_NULL)
    #print 'finish'
    loop = glib.MainLoop()
    t = threading.Timer(5., loop.quit)
    t.start()
    try:
        loop.run()
    except KeyboardInterrupt:
        pass
    print 'finish'
#if __name__ == '__main__':
#    import time
#    tcgen = LTCGenerator()
#    d = tcgen.frame_obj.get_all_obj()
#    #d['minute'].value = 1
#    #d['hour'].value = 2
#    d['second'].value = 58
#    d['frame'].value = 28
#    keys = ['hour', 'minute', 'second', 'frame']
#    values = tcgen.frame_obj.get_values()
#    #print ':'.join(['%02d' % (values[key]) for key in keys])
#    for i in range(61):
#        tcgen.frame_obj += 1
#        values = tcgen.frame_obj.get_values()
#        #print ':'.join(['%02d' % (values[key]) for key in keys]), '   ', i
#    a = tcgen.build_audio_data()
#    #print a
#    
