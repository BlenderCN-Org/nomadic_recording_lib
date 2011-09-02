import array
import colorsys
from BaseObject import BaseObject

colorprops = dict(zip(['red', 'green', 'blue', 'hue', 'sat', 'val'], [{'default':0.0}]*6))
#for key, val in colorprops.iteritems():
#    val.update({'fget':'_'.join([key, 'getter'])})

class Color(BaseObject):
    color_keys = ['red', 'green', 'blue']
    hsv_keys = ['hue', 'sat', 'val']
    _Properties = colorprops
    def __init__(self, **kwargs):
        self._rgb = [0.0] * 3
        self._hsv = [0.0] * 3
        super(Color, self).__init__(**kwargs)
        self._color_set_local = False
        self.bind(property_changed=self.on_own_property_changed)
        
    def set_value(self, *args, **kwargs):
        if len(args):
            if type(args[0]) == list or type(args[0]) == tuple:
                self._rgb = args[0]
            else:
                self._rgb = args
        else:
            self.rgb = kwargs
            
    @property
    def rgb(self):
        return dict(zip(self.color_keys, [getattr(self, key) for key in self.color_keys]))
        #return dict(zip(self.color_keys, self._rgb))
    @rgb.setter
    def rgb(self, value):
        self.set_rgb(**value)
        
    def set_rgb(self, **kwargs):
        self._color_set_local = True
        for key, val in kwargs.iteritems():
            if key in self.color_keys:
                setattr(self, key, val)
            #self._rgb[self.color_keys.index(key)] = val
        #self._hsv = list(colorsys.rgb_to_hsv(*self._rgb))
        self._update_hsv()
        self._color_set_local = False
            
    def set_hsv(self, **kwargs):
        self._color_set_local = True
        for x, key in enumerate(self.hsv_keys):
            val = kwargs.get(key)
            if val is not None and val != getattr(self, key):
                #self._hsv[x] = kwargs[key]
                setattr(self, key, kwargs[key])
        #self._rgb = list(colorsys.hsv_to_rgb(*self._hsv))
        self._update_rgb()
        self._color_set_local = False
        
    def _update_rgb(self):
        rgb = colorsys.hsv_to_rgb(*[getattr(self, key) for key in self.hsv_keys])
        for i, val in enumerate(rgb):
            setattr(self, self.color_keys[i], val * 255)
            
    def _update_hsv(self):
        hsv = colorsys.rgb_to_hsv(*[getattr(self, key) / 255. for key in self.color_keys])
        for i, val in enumerate(hsv):
            setattr(self, self.hsv_keys[i], val)
        
    @property
    def hsv(self):
        return dict(zip(self.hsv_keys, self.hsv_seq))
    @hsv.setter
    def hsv(self, value):
        self.set_hsv(**value)
        
    @property
    def hsv_seq(self):
        return [getattr(self, key) for key in self.hsv_keys]
        
#    def red_getter(self):
#        return self._rgb[0]
#    def green_getter(self):
#        return self._rgb[1]
#    def blue_getter(self):
#        return self._rgb[2]
#    def hue_getter(self):
#        return self._hsv[0]
#    def sat_getter(self):
#        return self._hsv[1]
#    def val_getter(self):
#        return self._hsv[2]
        
    def on_own_property_changed(self, **kwargs):
        if self._color_set_local:
            return
        prop = kwargs.get('Property')
        if prop.name in self.color_keys:
            #i = self.color_keys.index(prop.name)
            #self._rgb[i] = prop.value
            self.set_rgb(**{prop.name:prop.value})
        elif prop.name in self.hsv_keys:
            self.set_hsv(**{prop.name:prop.value})
            

arraytype_map = {'c':chr}

class PixelGrid(BaseObject):
    def __init__(self, **kwargs):
        super(PixelGrid, self).__init__(**kwargs)
        self.size = kwargs.get('size', (64, 64))
        self.pixels = []
        self.build_grid()
        
    def resize(self, **kwargs):
        self.clear_grid()
        self.size = kwargs.get('size')
        self.build_grid()
        
    def build_grid(self):
        for row in range(self.num_rows):
            line = []
            for col in range(self.num_cols):
                pixel = Color()
                line.append(pixel)
                pixel.bind(property_changed=self.on_pixel_changed)
            self.pixels.append(line)
    
    def clear_grid(self):
        for row in self.pixels:
            for pixel in row:
                pixel.unbind(self.on_pixel_changed)
        self.pixels = []
                
    @property
    def num_rows(self):
        return self.size[0]
    @property
    def num_cols(self):
        return self.size[1]
        
    def iterrows(self):
        return range(self.num_rows)
    def itercols(self):
        return range(self.num_cols)
        
    def get_ogl_pixel_data(self, **kwargs):
        color_format = kwargs.get('color_format', 'rgb')
        arraytype = kwargs.get('arraytype', 'c')
        a = array.array(arraytype)
        for y in self.iterrows():
            for x in self.itercols():
                pixel = self.pixels[y][x]
                keys = ['red', 'green', 'blue']
                for key in keys:
                    a.append(arraytype_map[arraytype](int(getattr(pixel, key))))
        return a
    
    def on_pixel_changed(self, **kwargs):
        pass
        
