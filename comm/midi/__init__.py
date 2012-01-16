#from pygame_midiIO import PyGameMidiIO

#MidiIO = PyGameMidiIO

#from portmidizero_midiIO import pmzMidiIO

#MidiIO = pmzMidiIO

from pyportmidi_midiIO import pypmMidiIO

MidiIO = pypmMidiIO

#from rtmidi_midiIO import rtmMidiIO

#MidiIO = rtmMidiIO

IO_LOADER = MidiIO
