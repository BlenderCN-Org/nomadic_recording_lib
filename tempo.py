import collections
import datetime

from BaseObject import BaseObject
from masterclock import MasterClock


def seconds_to_bpm(seconds):
    return 60. / seconds
    
def bpm_to_seconds(bpm):
    return 60. / bpm


class TapTempo(BaseObject):
    _Properties = {'tempo':dict(default=0., quiet=True), 
                   'tap':dict(default=False, quiet=True)}
    _minimum_tap_count = 2
    _maximum_tap_count = 4
    _maximum_tap_distance = 2  ##(seconds)
    def __init__(self, **kwargs):
        super(TapTempo, self).__init__(**kwargs)
        self.clock = MasterClock()
        self.clock.start()
        self.last_taps = collections.deque()
        self.bind(tap=self._on_tap)
        
    def unlink(self):
        super(TapTempo, self).unlink()
        self.clock.stop()
        
    def _on_tap(self, **kwargs):
        if not kwargs.get('value'):
            return
        self.last_taps.append(self.clock.clock_seconds)
        self.tap = False
        if len(self.last_taps) >= self._minimum_tap_count:
            self.calculate_tempo()
            
    def calculate_tempo(self):
        if len(self.last_taps) < self._minimum_tap_count:
            return
        if len(self.last_taps) > self._maximum_tap_count:
            t = self.last_taps.popleft()
        remove_tap = None
        tapsum = 0.
        for i, tap in enumerate(self.last_taps):
            if i == 0:
                continue
            lasttap = self.last_taps[i-1]
            diff = tap - lasttap
            if diff > self._maximum_tap_distance:
                remove_tap = i - 1
                break
            tapsum += diff
        if remove_tap is not None:
            del self.last_taps[remove_tap]
            return self.calculate_tempo()
        avg = tapsum / len(self.last_taps)
        self.tempo = seconds_to_bpm(avg)
