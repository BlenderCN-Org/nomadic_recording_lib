from gi.repository import Gtk
import parser
import network_objects

class TreeStore(object):
    def __init__(self, **kwargs):
        self.column_types = kwargs.get('column_types')
        self.column_attr_map = kwargs.get('column_attr_map')
        self.root_obj = kwargs.get('root_obj')
        self.child_attrs = kwargs.get('child_attrs')
        self.children = {}
        self.store = Gtk.TreeStore(*self.column_types)
        self.root_child = TreeItem(tree_root=self)
        
class TreeItem(object):
    def __init__(self, **kwargs):
        self.obj = kwargs.get('object')
        self.tree_root = kwargs.get('tree_root')
        self.tree_parent = kwargs.get('tree_parent')
        self.attr_map = self.tree_root.attr_map[self.obj.__class__.__name__]
        self.child_attr = self.tree_root.child_attrs.get(self.obj.__class__.__name__)
        self.iter = self.add_to_tree()
        self.children = {}
        if self.child_attr is not None:
            self.add_children()
    def add_to_tree(self):
        vals = []
        column_types = self.tree_root.column_types
        for i, attr in enumerate(self.attr_map):
            t = column_types[i]
            vals.append(t(getattr(self.obj, attr)))
        if self.tree_parent is None:
            args = [vals]
        else:
            args = [self.tree_parent, vals]
        iter = self.tree_root.store.append(*args)
        return iter
    def add_children(self):
        child_vals = getattr(self.obj, self.child_attr)
        ckwargs = {'tree_root':self.tree_root, 'tree_parent':self}
        if isinstance(child_vals, dict):
            for k, v in child_vals.iteritems():
                ckwargs['object'] = v
                child = TreeItem(**ckwargs)
                self.children[k] = child
        else:
            for i, v in enumerate(child_vals):
                ckwargs['object'] = v
                child = TreeItem(**ckwargs)
                self.children[i] = child
                
def test(**kwargs):
    net_conf, net_parse = parser.parse_conf(filename='dhcpd.conf', return_parsed=True)
    lease_conf = parser.parse_leases(filename='dhcpd.leases')
    nets = network_objects.build_networks(net_conf)
    leases = network_objects.build_leases(lease_conf)
    return {'PARSED_NETWORKS':net_conf, 
            'PARSED_SECTIONS':net_parse, 
            'PARSED_LEASES':lease_conf, 
            'NETWORKS':nets, 
            'LEASES':leases}
