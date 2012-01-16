import rtmidi


from midi_io import MidiIO, MidiIn, MidiOut, DeviceInfo

class rtmMidiIO(MidiIO):
    def __init__(self, **kwargs):
        self.io_device_classes = {'in':rtmMidiIn, 'out':rtmMidiOut}
        super(rtmMidiIO, self).__init__(**kwargs)
        
    def update_devices(self):
        input = rtmidi.RtMidiIn()
        for i in range(input.getPortCount()):
            info = ['', input.getPortName(i), 1, 0, 0]
            dev = self.dev_info['in'].add_child(DeviceInfo, info=info)
            dev.bind(active=self.on_dev_info_active_set)
        output = rtmidi.RtMidiOut()
        for i in range(output.getPortCount()):
            info = ['', output.getPortName(i), 0, 1, 0]
            dev = self.dev_info['out'].add_child(DeviceInfo, info=info)
            dev.bind(active=self.on_dev_info_active_set)
        
class rtmMidiIn(MidiIn):
    def build_device(self, **kwargs):
        return rtmidi.RtMidiIn()
    def _on_state_set(self, **kwargs):
        state = kwargs.get('value')
        if state:
            self.device.openPort(self.dev_info.index)
        else:
            self.device.closePort()
        
class rtmMidiOut(MidiOut):
    def build_device(self, **kwargs):
        return rtmidi.RtMidiOut()
        
    def send(self, **kwargs):
        data = kwargs.get('data')
        timestamp = kwargs.get('timestamp', 0)
        sysex = kwargs.get('sysex')
        msg = kwargs.get('msg')
        if not self.state:
            return
        if sysex is not None:
            #self.device.write_sys_ex(timestamp, sysex)
            pass
        else:
            m = rtmidi.MidiMessage(*data)
            #d = {'channel':'setChannel', 'note':'setNoteNumber', 'velocity':'setVelocity', 
            #     'controller':'set
            self.device.sendMessage(m)
    def _on_state_set(self, **kwargs):
        state = kwargs.get('value')
        if state:
            self.device.openPort(self.dev_info.index)
        else:
            self.device.closePort()
