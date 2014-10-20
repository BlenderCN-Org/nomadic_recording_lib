import datetime
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
    def get_child_classes(self):
        return []
    @property
    def attribute_registry(self):
        r = getattr(self, '_attribute_registry', None)
        if r is None and self.root_node is not None:
            r = self.root_node.attribute_registry
        return r
    @attribute_registry.setter
    def attribute_registry(self, value):
        if value is not None:
            if not isinstance(value, AttributeRegistry):
                value = AttributeRegistry(**value)
            value.parent = self
        self._attribute_registry = value
    @property
    def root_node(self):
        node = getattr(self, '_root_node', None)
        if node is None:
            if self.parent is not None:
                node = self.parent.root_node
        return node
    @root_node.setter
    def root_node(self, value):
        if value is not None:
            if not isinstance(value, Node):
                value = Node(**value)
            value.parent = self
        self._root_node = value
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
        
class Node(Element):
    tag_name = 'node'
    def do_init(self, **kwargs):
        self.id = kwargs.get('id')
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
        obj = super(Node, self).add_child(cls, **kwargs)
        if cls == NodeAttribute:
            self.attributes.append(obj)
        elif cls == NodeLink:
            self.node_links[obj.id] = obj
        elif cls == Node:
            self.child_nodes[obj.id] = obj
        return obj
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
        
class NodeAttribute(Element):
    tag_name = 'attribute'
    def do_init(self, **kwargs):
        self.name = kwargs.get('name')
        self.value = kwargs.get('value')
    @property
    def registered_attribute(self):
        registry = self.attribute_registry
        if registry is None:
            return None
        return registry.get(self.name)
        
class NodeLink(Element):
    tag_name = 'arrowlink'
    def do_init(self, **kwargs):
        self.id = kwargs.get('id')
        self.destination_id = kwargs.get('destination')
        self.node = kwargs.get('node')
    def get_dict(self):
        d = super(NodeLink, self).get_dict()
        d['destination'] = self.destination_id
        return d
