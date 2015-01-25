import operator

try:
    import bpy
except:
    pass

def find_sound_clip():
    vse = bpy.context.scene.sequence_editor
    for clip in vse.sequences_all:
        if clip.type == 'SOUND':
            return clip
            
FILENAME = find_sound_clip().filepath

def get_screen(screen_type):
    for window in bpy.context.window_manager.windows:
        screen = window.screen
        for area in screen.areas:
            if area.type == screen_type:
                return {'window':window, 'screen':screen, 'area':area}
    
def bake_sound(**kwargs):
    obj = kwargs.get('obj')
    sound_file = kwargs.get('file')
    freq_range = kwargs.get('range')
    attack = kwargs.get('attack', .005)
    release = kwargs.get('release', .2)
    def build_keyframe():
        obj.keyframe_insert(data_path='scale', index=2, frame=1)
    def do_bake():
        bpy.ops.graph.sound_bake(filepath=sound_file, low=freq_range[0], high=freq_range[1],
                                 attack=attack, release=release)
    build_keyframe()
    override = get_screen('GRAPH_EDITOR')
    bpy.ops.screen.screen_full_area(override)
    do_bake()
    bpy.ops.screen.back_to_previous()
    

CENTER_FREQUENCY = 1000.
FREQUENCY_RANGE = [20., 20000.]

class FreqBand():
    def __init__(self, **kwargs):
        self.index = kwargs.get('index')
        self.octave_divisor = kwargs.get('octave_divisor', 1.)
        self.center = self.calc_center()
        self.range = self.calc_range()
    def calc_center(self):
        f = CENTER_FREQUENCY
        if self.index == 0.:
            return f
        count = int(self.index)
        if self.index > 0.:
            op = operator.mul
        else:
            op = operator.truediv
            count *= -1
        for i in range(count):
            f = op(f, 2 ** (1. / self.octave_divisor))
        return f
    def calc_range(self):
        f = self.center
        lower = f / (2 ** (1. / self.octave_divisor / 2.))
        upper = f * (2 ** (1. / self.octave_divisor / 2.))
        if lower < FREQUENCY_RANGE[0]:
            lower = FREQUENCY_RANGE[0]
        if upper > FREQUENCY_RANGE[1]:
            upper = FREQUENCY_RANGE[1]
        return [lower, upper]
    def __str__(self):
        return '%s<%s>%s' % (self.range[0], self.center, self.range[1])
class Spectrum():
    def __init__(self, **kwargs):
        self.octave_divisor = kwargs.get('octave_divisor', 1.)
        self.bands = {}
        self.build_bands()
    def build_bands(self):
        center = CENTER_FREQUENCY
        i = 0.
        while center < FREQUENCY_RANGE[1]:
            band = FreqBand(index=i, octave_divisor=self.octave_divisor)
            center = band.center
            if center > FREQUENCY_RANGE[1]:
                break
            self.bands[center] = band
            i += 1.
        center = CENTER_FREQUENCY
        i = 0.
        while center > FREQUENCY_RANGE[0]:
            band = FreqBand(index=i, octave_divisor=self.octave_divisor)
            center = band.center
            if center < FREQUENCY_RANGE[0]:
                break
            i -= 1.
            if center in self.bands:
                continue
            self.bands[center] = band
    def iterkeys(self):
        for key in sorted(self.bands.keys()):
            yield key
    def itervalues(self):
        for key in self.iterkeys():
            yield self.bands[key]
    def iteritems(self):
        for key in self.iterkeys():
            yield key, self.bands[key]
    def keys(self):
        return [key for key in self.iterkeys()]
    def values(self):
        return [val for val in self.itervalues()]
    def items(self):
        return [(key, val) for key, val in self.iteritems()]

def build_base_cube():
    bpy.ops.mesh.primitive_cube_add()
    obj = bpy.context.active_object
    obj.name = 'soundbake.cube'
    obj.data.name = 'soundbake.cube'
    obj.location = [0., 0., 0.]
    return obj
    
def setup_scene():
    bpy.ops.object.add(type='EMPTY', location=[0., 0., 0.])
    parent = bpy.context.active_object
    base_cube = build_base_cube()
    spectrum = Spectrum()
    cube = None
    for key, band in spectrum.iteritems():
        if cube is None:
            cube = base_cube
        else:
            bpy.ops.object.add(type='MESH')
            cube = bpy.context.active_object
            cube.data = base_cube.data
            #print(band.center, band.index, band.index * 2.)
            #bpy.context.scene.update()
        cube.name = 'soundbake.cube.%s' % (key)
        cube.location = [band.index * 2., 0., 0.]
        bake_sound(obj=cube, file=FILENAME, range=band.range)
        cube.parent = parent
        cube.select = False
setup_scene()
    
