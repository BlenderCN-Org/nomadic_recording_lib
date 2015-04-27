import gzip
import xml.etree.ElementTree as ET
    
class XMLNode(object):
    def __init__(self, **kwargs):
        self.node = kwargs.get('node')
        self.parent = kwargs.get('parent')
        self.index = kwargs.get('index', 0)
        tree_depth = kwargs.get('tree_depth')
        if tree_depth is None:
            if self.parent is None:
                tree_depth = 0
            else:
                tree_depth = self.parent.tree_depth + 1
        self.tree_depth = tree_depth
        self.children = []
        self.build_children()
    @property
    def uid(self):
        if self.parent is not None:
            uid = '_'.join([self.parent.uid, str(self.index)])
        else:
            uid = 'root'
        return uid
    @property
    def root(self):
        p = self.parent
        if p is None:
            return self
        return p.root
    @property
    def tag(self):
        return self.node.tag
    @property
    def text(self):
        if len(self.children):
            return None
        return self.node.text
    def get(self, key, default=None):
        return self.node.get(key, default)
    def build_children(self):
        for i, node in enumerate(self.node):
            self.add_child(node=node, index=i)
    def add_child(self, cls=None, **kwargs):
        kwargs.setdefault('parent', self)
        if cls is None:
            cls = self.__class__
        obj = cls(**kwargs)
        self.children.append(obj)
        return obj
    def serialize(self):
        d = {
            'tag':self.tag, 
            'attrs':self.node.attrs, 
            'children':[], 
        }
        for child in self:
            d['children'].append(child.serialize())
        return d
    def iter_children(self):
        for c in self.children:
            yield c
    def walk(self):
        iters = [[self], self.iter_children()]
        for obj_iter in iters:
            for obj in obj_iter:
                if obj is self:
                    walk_iter = [obj]
                else:
                    walk_iter = obj.walk()
                for item in walk_iter:
                    yield item
    def __iter__(self):
        return self.iter_children()
    def __repr__(self):
        return str(self)
    def __str__(self):
        return self.tag
        
class ALSNode(XMLNode):
    @property
    def value(self):
        value = self.get('Value')
        if value is None:
            return value
        if value.isdigit():
            if '.' in value:
                return float(value)
            else:
                return int(value)
        elif value in ['true', 'false']:
            return value == 'true'
        return value
    @property
    def sec_time(self):
        t = self.get('SecTime')
        if t is None:
            return t
        return float(t)
    @property
    def beat_time(self):
        t = self.get('BeatTime')
        if t is None:
            return t
        if '.' in t:
            return float(t)
        else:
            return int(t)
        
def read_als(filename):
    with gzip.open(filename, 'rb') as f:
        s = f.read()
    return s
    
def parse_als(filename):
    s = read_als(filename)
    xml_root = ET.fromstring(s)
    als_root = ALSNode(node=xml_root)
    return als_root
