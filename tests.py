from comm.CommDispatcher import CommDispatcherBase


class CommDispatcher(CommDispatcherBase):
    def __init__(self, **kwargs):
        super(CommDispatcher, self).__init__(**kwargs)
        self.osc_io = self.build_io_module('osc')
        self.midi_io = self.build_io_module('midi')
    def shutdown(self):
        self.midi_io.do_disconnect(blocking=True)
        self.osc_io.shutdown()
        super(CommDispatcher, self).shutdown()

comm = CommDispatcher()
print comm.IO_MODULES
comm.shutdown()

