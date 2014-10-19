import datetime
import xml.etree.ElementTree as ET

class Color(object):
    def __init__(self, **kwargs):
        self.red = kwargs.get('red')
        self.green = kwargs.get('green')
        self.blue = kwargs.get('blue')
        
def parse_color(color):
    if isinstance(color, basestring):
        color = color.strip('#')
        d = {}
        for key in ['red', 'green', 'blue']:
            d[key] = color[:2]
            if len(color):
                color = color[2:]
    if isinstance(color, dict):
        color = Color(**d)
    return color
def parse_dt(dt):
    if isinstance(dt, datetime.datetime):
        return dt
    if isinstance(dt, basestring):
        dt = int(dt)
    return datetime.datetime.fromtimestamp(dt/1000.)
    
class Element(object):
    def __init__(self, **kwargs):
        self.parent = kwargs.get('parent')
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
    
class MindMap(Element):
    tag_name = 'map'
    def __init__(self, **kwargs):
        self.version = kwargs.get('version')
        self.attribute_registry = kwargs.get('attribute_registry')
        self.root_node = kwargs.get('root_node')
        super(MindMap, self).__init__(**kwargs)
        
class AttributeRegistry(Element):
    tag_name = 'attribute_registry'
    def __init__(self, **kwargs):
        super(AttributeRegistry, self).__init__(**kwargs)
        self.attributes = {}
        for key, val in kwargs.get('attributes', {}).iteritems():
            val.setdefault('name', key)
            self.add_attribute(**val)
    def add_attribute(self, **kwargs):
        kwargs['parent'] = self
        attr = RegisteredAttribute(**kwargs)
        self.attributes[attr.name] = attr
    def get(self, name, default=None):
        return self.attributes.get(name, default)
        
class RegisteredAttribute(Element):
    tag_name = 'attribute_name'
    def __init__(self, **kwargs):
        super(RegisteredAttribute, self).__init__(**kwargs)
        self.name = kwargs.get('name')
        self.visible = kwargs.get('visible')
        
class Node(Element):
    tag_name = 'node'
    def __init__(self, **kwargs):
        super(Node, self).__init__(**kwargs)
        self.id = kwargs.get('id')
        self.created = parse_dt(kwargs.get('created'))
        self.modified = parse_dt(kwargs.get('modified'))
        self.text = kwargs.get('text')
        self.color = parse_color(kwargs.get('color'))
        self.background_color = parse_color(kwargs.get('background_color'))
        self.position = kwargs.get('position')
        self.style = kwargs.get('style')
        self.attributes = {}
        self.node_links = {}
        for key, val in kwargs.get('attributes', {}).iteritems():
            val.setdefault('name', key)
            self.add_attribute(**val)
        for link in kwargs.get('node_links', []):
            self.add_node_link(**link)
    def add_attribute(self, **kwargs):
        kwargs['parent'] = self
        attr = NodeAttribute(**kwargs)
        self.attributes.append(attr)
    def add_node_link(self, node):
        if isinstance(node, Node):
            self.node_links[node.id] = node
        else:
            self.node_links[node] = None
        
class NodeAttribute(Element):
    def __init__(self, **kwargs):
        super(NodeAttribute, self).__init__(**kwargs)
        self.name = kwargs.get('name')
        self.value = kwargs.get('value')
        self.registered_attribute = self.attribute_registry.get(self.name)
        
