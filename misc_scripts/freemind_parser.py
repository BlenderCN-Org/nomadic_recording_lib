import datetime
import random
import json
import xml.etree.ElementTree as ET

class Color(object):
    def __init__(self, **kwargs):
        self.red = kwargs.get('red')
        self.green = kwargs.get('green')
        self.blue = kwargs.get('blue')
    def to_hex(self):
        l = []
        for attr in ['red', 'green', 'blue']:
            l.append(hex(getattr(self, attr)).split('0x')[1])
        return '#%s' % (''.join(l))
        
def parse_color(color):
    if isinstance(color, basestring):
        color = color.strip('#')
        d = {}
        for key in ['red', 'green', 'blue']:
            d[key] = int(color[:2], 16)
            if len(color):
                color = color[2:]
        color = d
    if isinstance(color, dict):
        color = Color(**d)
    return color

DT_FMT_STR = '%Y%m%d-%H:%M:%S.%f'
def parse_dt(dt):
    if isinstance(dt, datetime.datetime):
        return dt
    if isinstance(dt, basestring):
        if dt.isdigit:
            dt = int(dt)
        else:
            return datetime.datetime.strptime(dt, DT_FMT_STR)
    return datetime.datetime.fromtimestamp(dt/1000.)

def dt_to_str(dt):
    return dt.strftime(DT_FMT_STR)
    
class Element(object):
    def __init__(self, **kwargs):
        self.parent = kwargs.get('parent')
        self.etree_element = kwargs.get('etree_element')
        self.element_attributes = kwargs.get('element_attributes')
        self.children = {}
        self.do_init(**kwargs)
        if self.etree_element is not None:
            self.find_children_from_etree()
        if self.parent is None:
            self.post_init()
    def do_init(self, **kwargs):
        pass
    def post_init(self):
        for child_list in self.children.itervalues():
            for child in child_list:
                child.post_init()
    def get_child_classes(self):
        return []
    @property
    def root_element(self):
        if self.parent is None:
            return self
        return self.parent.root_element
    def add_child(self, cls, **kwargs):
        element = kwargs.get('etree_element')
        kwargs['parent'] = self
        if element is not None:
            kwargs = kwargs.copy()
            del kwargs['etree_element']
            obj = cls.from_etree(element, **kwargs)
        else:
            obj = cls(**kwargs)
        if cls.__name__ not in self.children:
            self.children[cls.__name__] = []
        self.children[cls.__name__].append(obj)
        return obj
    @classmethod
    def from_etree(cls, element, **kwargs):
        keys = element.keys()
        d = dict(zip([key.lower() for key in keys], [element.get(key) for key in keys]))
        kwargs['element_attributes'] = d
        for key, val in d.iteritems():
            kwargs.setdefault(key, val)
        kwargs['etree_element'] = element
        return cls(**kwargs)
    def find_children_from_etree(self):
        classes = self.get_child_classes()
        element = self.etree_element
        for cls in classes:
            for c_element in element.findall(cls.tag_name):
                self.add_child(cls, etree_element=c_element)
    def get_dict(self):
        return self.element_attributes.copy()
    def __repr__(self):
        return '<%s (%s)>' % (self.__class__.__name__, self)
    def __str__(self):
        return '%s: %s' % (self.tag_name, self.element_attributes)
        
class MindMap(Element):
    tag_name = 'map'
    def do_init(self, **kwargs):
        self.version = kwargs.get('version')
        self.attribute_registry = kwargs.get('attribute_registry')
        self.root_node = kwargs.get('root_node')
    @classmethod
    def from_xml(cls, source):
        tree = ET.parse(source)
        return cls.from_etree(tree.getroot())
    def to_json(self, pretty=True):
        d = self.get_dict()
        jkwargs = {}
        if pretty:
            jkwargs['indent'] = 2
        return json.dumps(d, **jkwargs)
    def to_sigma_json(self, size=None):
        if size is None:
            size = [1000, 1000]
        return self.root_node.to_sigma_json(size)
    def add_child(self, cls, **kwargs):
        obj = super(MindMap, self).add_child(cls, **kwargs)
        if cls == AttributeRegistry:
            self.attribute_registry = obj
        elif cls == Node:
            self.root_node = obj
        return obj
    def get_child_classes(self):
        return [AttributeRegistry, Node]
    def get_dict(self):
        d = super(MindMap, self).get_dict()
        d['attribute_registry'] = self.attribute_registry.get_dict()
        d['root_node'] = self.root_node.get_dict()
        return d
        
class AttributeRegistry(Element):
    tag_name = 'attribute_registry'
    def do_init(self, **kwargs):
        self.attributes = {}
        for key, val in kwargs.get('attributes', {}).iteritems():
            val.setdefault('name', key)
            self.add_child(RegisteredAttribute, **val)
    def get_child_classes(self):
        return [RegisteredAttribute]
    def add_child(self, cls, **kwargs):
        attr = super(AttributeRegistry, self).add_child(cls, **kwargs)
        self.attributes[attr.name] = attr
        return attr
    def get(self, name, default=None):
        return self.attributes.get(name, default)
    def get_dict(self):
        d = super(AttributeRegistry, self).get_dict()
        d['attributes'] = {}
        for key, val in self.attributes.iteritems():
            d['attributes'][key] = val.get_dict()
        return d
        
class RegisteredAttribute(Element):
    tag_name = 'attribute_name'
    def do_init(self, **kwargs):
        self.name = kwargs.get('name')
        self.visible = kwargs.get('visible')
        
class NodeBase(Element):
    @property
    def root_node(self):
        if isinstance(self.parent, Node):
            return self.parent.root_node
        self._is_root = True
        return self
    @property
    def attribute_registry(self):
        root = self.root_node
        r = getattr(root, '_attribute_registry', None)
        if r is None:
            r = root._attribute_registry = root.parent.attribute_registry
        return r
class Node(NodeBase):
    tag_name = 'node'
    node_size = [24, 12]
    node_spacing = [6, 3]
    _is_root = False
    def do_init(self, **kwargs):
        self.id = kwargs.get('id')
        self.nest_level = kwargs.get('nest_level', 0)
        self.index = kwargs.get('index', 0)
        self.x = 0
        self.y = 0
        self.created = parse_dt(kwargs.get('created'))
        self.modified = parse_dt(kwargs.get('modified'))
        self.text = kwargs.get('text')
        self.color = parse_color(kwargs.get('color'))
        self.background_color = parse_color(kwargs.get('background_color'))
        self.position = kwargs.get('position')
        self.style = kwargs.get('style')
        self.child_nodes = {}
        self.attributes = []
        self.node_links = {}
        for val in kwargs.get('attributes', []):
            self.add_child(NodeAttribute, **val)
        for link in kwargs.get('node_links', []):
            self.add_node_link(NodeLink, **link)
        for key, val in kwargs.get('child_nodes', {}).iteritems():
            val.setdefault('id', key)
            self.add_child(Node, **val)
    def get_child_classes(self):
        return [NodeAttribute, NodeLink, Node]
    def add_child(self, cls, **kwargs):
        if cls == Node:
            kwargs['nest_level'] = self.nest_level + 1
            kwargs['index'] = len(self.child_nodes)
        obj = super(Node, self).add_child(cls, **kwargs)
        if cls == NodeAttribute:
            self.attributes.append(obj)
        elif cls == NodeLink:
            self.node_links[obj.id] = obj
        elif cls == Node:
            self.child_nodes[obj.id] = obj
        return obj
    def find_by_id(self, node_id):
        if node_id in self.child_nodes:
            return self.child_nodes[node_id]
        for child in self.child_nodes.itervalues():
            node = child.find_by_id(node_id)
            if node is not None:
                return node
        return None
    def find_max_nest_and_index(self, x_axis=None):
        if x_axis is None:
            x_axis = []
        x = self.nest_level
        y = len(self.child_nodes)
        if len(x_axis) < x + 1:
            x_axis.append(0)
        x_axis[x] += y
        for child in self.child_nodes.itervalues():
            _x, x_axis = child.find_max_nest_and_index(x_axis)
            if _x > x:
                x = _x
        if self._is_root:
            max_y = 0
            for nest_level, y in enumerate(x_axis):
                if y > max_y:
                    max_y = y
            return {'max_nest':x, 'max_index':max_y, 'x_axis':x_axis}
        else:
            return x, x_axis
    def calc_positions(self):
        d = self.find_max_nest_and_index()
        d['canvas_size'] = [
            d['max_index'] * (self.node_size[0] + self.node_spacing[0]), 
            d['max_nest'] * (self.node_size[1] + self.node_spacing[1]), 
        ]
        self.y = d['canvas_size'][1] / 2
        self.x = 0
        for child in self.child_nodes.itervalues():
            child._calc_position(d)
    def _calc_position(self, d):
        self.x = (self.nest_level * self.node_size[0]) + self.node_spacing[0]
        if d['x_axis'][self.nest_level] == 0:
            self.y = self.parent.y
        else:
            #y_size = d['canvas_size'][1] / (d['x_axis'][self.nest_level] * (self.node_size[1] + self.node_spacing[1]))
            #self.y = (y_size / (self.index + 1)) + self.parent.y
            self.y = ((self.node_size[1] + self.node_spacing[1]) * self.index) + self.parent.y
        for child in self.child_nodes.itervalues():
            child._calc_position(d)
    def to_sigma_json(self, size, d=None):
        if d is None:
            d = {'nodes':[], 'edges':[]}
        self.calc_positions()
        d, obj_count = self._build_sigma_json_nodes(size, d)
        d = self._build_sigma_json_links(d)
        return json.dumps(d, indent=2)
    def _build_sigma_json_nodes(self, size, d):
        node = {
            'id':self.id, 
            'label':self.text, 
            'x':self.x, #random.random() * size[0], 
            'y':self.y, #random.random() * size[1], 
            'size':8
        }
        c = self.background_color
        if c is None:
            c = Color(red=96, blue=96, green=96)
        node['color'] = c.to_hex()
        d['nodes'].append(node)
        obj_count = len(self.child_nodes)
        for child in self.child_nodes.itervalues():
            d, _obj_count = child._build_sigma_json_nodes(size, d)
            obj_count += _obj_count
        #node['y'] = node['y'] + (obj_count / 2)
        return d, obj_count
    def _build_sigma_json_links(self, d):
        for child_id, child in self.child_nodes.iteritems():
            link = {
                'id':'-'.join([self.id, child_id]), 
                'source':self.id, 
                'target':child_id, 
            }
            d['edges'].append(link)
            d = child._build_sigma_json_links(d)
        return d
    def get_dict(self):
        d = super(Node, self).get_dict()
        d['created'] = dt_to_str(self.created)
        d['modified'] = dt_to_str(self.modified)
        for attr in ['color', 'background_color']:
            c = getattr(self, attr)
            if c is None:
                continue
            d[attr] = c.to_hex()
        for attr in ['attributes', 'node_links', 'child_nodes']:
            coll = getattr(self, attr)
            if isinstance(coll, list):
                d[attr] = []
                for obj in coll:
                    d[attr].append(obj.get_dict())
            else:
                d[attr] = {}
                for key, val in coll.iteritems():
                    d[attr][key] = val.get_dict()
        return d
        
class NodeAttribute(NodeBase):
    tag_name = 'attribute'
    def do_init(self, **kwargs):
        self.name = kwargs.get('name')
        self.value = kwargs.get('value')
        self.registered_attribute = kwargs.get('registered_attribute')
    def post_init(self):
        if self.registered_attribute is None:
            self.registered_attribute = self.attribute_registry.get(self.name)
        super(NodeAttribute, self).post_init()
        
class NodeLink(NodeBase):
    tag_name = 'arrowlink'
    def do_init(self, **kwargs):
        self.id = kwargs.get('id')
        self.destination_id = kwargs.get('destination')
        self.node = kwargs.get('node')
    def post_init(self):
        if self.node is None:
            self.node = self.root_node.find_by_id(self.destination_id)
        super(NodeLink, self).post_init()
    def get_dict(self):
        d = super(NodeLink, self).get_dict()
        d['destination'] = self.destination_id
        return d
