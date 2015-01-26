import math
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

def build_base_cube(**kwargs):
    name = kwargs.get('name', 'soundbake.cube')
    data_name = kwargs.get('data_name', 'soundbake.cube')
    bpy.ops.mesh.primitive_cube_add()
    obj = bpy.context.active_object
    obj.name = name
    obj.data.name = data_name
    obj.location = [0., 0., 0.]
    return obj
    
class Cube():
    def __init__(self, **kwargs):
        self.band = kwargs.get('band')
        self.offset_index = kwargs.get('offset_index', 0)
        self.parent = kwargs.get('parent')
        self.mesh = kwargs.get('mesh')
        self.material = kwargs.get('material')
        self.name = 'soundbake.cube.%s.%03d' % (self.band.center, self.offset_index)
        if self.material is None:
            bpy.ops.material.new()
            self.material = bpy.data.materials[len(bpy.data.materials)-1]
            self.material.name = 'soundbake.cube'
        if self.mesh is None:
            self.obj = build_base_cube(name=self.name)
            self.mesh = self.obj.data
            self.mesh.materials.append(self.material)
        else:
            bpy.ops.object.add(type='MESH')
            self.obj = bpy.context.active_object
            self.obj.data = self.mesh
            self.obj.name = self.name
        self.update_scene()
        y = self.offset_index * 2.
        if isinstance(self.parent, Cube):
            x = 0.
            pobj = self.parent.obj
        else:
            x = self.band.index * 2.
            self.obj.scale = [1., 1., math.log10(self.band.center)]
            bpy.ops.object.transform_apply(scale=True)
            pobj = self.parent
        self.obj.location = [x, y, 0.]
        self.obj.parent = pobj
        self.update_scene()
    @property
    def need_update(self):
        return self.obj.is_updated or self.obj.is_updated_data
    def update_scene(self):
        if not self.need_update:
            return
        bpy.context.scene.update()
    def set_slow_parent(self):
        self.update_scene()
        if self.offset_index > 0:
            self.obj.use_slow_parent = True
            self.obj.slow_parent_offset = self.offset_index
        self.update_scene()
    
    
class BakedCube(Cube):
    def __init__(self, **kwargs):
        super(BakedCube, self).__init__(**kwargs)
        self.offset_count = kwargs.get('offset_count', 10)
        self.children = {}
        ckwargs = dict(parent=self, band=self.band, mesh=self.mesh)
        for i in range(self.offset_count):
            ckwargs['offset_index'] = i + 1
            cube = Cube(**ckwargs)
            self.children[i] = cube
    def bake_sound(self, filename):
        for obj in bpy.context.selected_objects:
            obj.select = False
        self.obj.select = True
        bake_sound(obj=self.obj, file=filename, range=self.band.range)
        self.update_scene()
        for i in sorted(self.children):
            child = self.children[i]
            child.set_slow_parent()
        
def setup_scene():
    bpy.ops.object.add(type='EMPTY', location=[0., 0., 0.])
    parent = bpy.context.active_object
    spectrum = Spectrum()
    cubes = []
    material = None
    for key, band in spectrum.iteritems():
        cube = BakedCube(parent=parent, band=band, material=material)
        cubes.append(cube)
        if material is None:
            material = cube.material
    for cube in cubes:
        cube.bake_sound(FILENAME)
setup_scene()
