import array
import bisect
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
        super(Color, self).__init__(**kwargs)
        self._color_set_local = False
        self.bind(property_changed=self.on_own_property_changed)
            
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
        self._update_hsv()
        self._color_set_local = False
            
    def set_hsv(self, **kwargs):
        self._color_set_local = True
        for key, val in kwargs.iteritems():
            if key in self.hsv_keys:
                setattr(self, key, val)
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
    hsv_keys = ['hue', 'sat', 'val']
    def __init__(self, **kwargs):
        super(PixelGrid, self).__init__(**kwargs)
        self.pixels_by_hsv = {}
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
                pixel.grid_location = {'row':row, 'col':col}
                self.add_pixel_to_hsv_dict(pixel)
                line.append(pixel)
                pixel.bind(property_changed=self.on_pixel_changed)
            self.pixels.append(line)
        
    def add_pixel_to_hsv_dict(self, pixel):
        h, s, v = pixel.hsv_seq
        if h not in self.pixels_by_hsv:
            self.pixels_by_hsv[h] = {}
        if s not in self.pixels_by_hsv[h]:
            self.pixels_by_hsv[h][s] = {}
        if v not in self.pixels_by_hsv[h][s]:
            self.pixels_by_hsv[h][s][v] = []
        self.pixels_by_hsv[h][s][v].append(pixel)
    
    def clear_grid(self):
        for row in self.pixels:
            for pixel in row:
                pixel.unbind(self.on_pixel_changed)
        self.pixels_by_hsv.clear()
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
        
    def find_pixels_from_hsv(self, hsv):
        if isinstance(hsv, dict):
            hsv = [hsv[key] for key in self.hsv_keys]
        d = self.pixels_by_hsv
        for i, value in enumerate(hsv):
            l = sorted(d.keys())
            index = bisect.bisect_left(l, value)
            if index == len(l):
                key = l[index-1]
            else:
                key = l[index]
            if index != 0:
                last = l[index-1]
                if value - last < key - value:
                    key = last
            d = d[key]
        return d
        
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
        def remove_old_location(pixel, old):
            h = self.pixels_by_hsv.get(old['hue'])
            if not h:
                return
            s = h.get(old['sat'])
            if not s:
                return
            v = s.get(old['val'])
            if not v:
                return
            if pixel in v:
                del v[v.index(pixel)]
            if not len(v):
                del s[old['val']]
            if not len(s):
                del h[old['sat']]
            if not len(h):
                del self.pixels_by_hsv[old['hue']]
        prop = kwargs.get('Property')
        if prop.name in self.hsv_keys:
            pixel = kwargs.get('obj')
            old = kwargs.get('old')
            oldhsv = pixel.hsv
            oldhsv[prop.name] = old
            remove_old_location(pixel, oldhsv)
            self.add_pixel_to_hsv_dict(pixel)
            
        
if __name__ == '__main__':
    grid = PixelGrid(size=(16, 16))
    for y, row in enumerate(grid.pixels):
        for x, pixel in enumerate(row):
            pixel.red = y * 255. / grid.num_rows
            pixel.green = (y * -255. / grid.num_rows) + 255
            pixel.blue = x * 255. / grid.num_cols
    d = {}
    for hkey, hval in grid.pixels_by_hsv.iteritems():
        d[hkey] = {}
        for skey, sval in hval.iteritems():
            d[hkey][skey] = {}
            for vkey, vval in sval.iteritems():
                d[hkey][skey][vkey] = [p.hsv_seq for p in vval]
    p = grid.find_pixels_from_hsv([1., 1., 1.])
    print p[0].hsv
    
