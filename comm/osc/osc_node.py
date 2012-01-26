import sys
import threading
import datetime
if __name__ == '__main__':
    import sys
    import os.path
    p = os.path.dirname(__file__)
    for i in range(2):
        p = os.path.split(p)[0]
    sys.path.append(p)
from Bases import BaseObject
from messages import Address, Message, Bundle, parse_message

OSC_EPOCH = datetime.datetime(1900, 1, 1, 0, 0, 0)

def seconds_from_timedelta(td):
    return td.seconds + td.days * 24 * 3600 + (td.microseconds / float(10**6))

def timetag_to_datetime(**kwargs):
    timetag_obj = kwargs.get('timetag_obj')
    if timetag_obj is not None:
        value = timetag_obj.value
    else:
        value = kwargs.get('value')
    td = datetime.timedelta(seconds=value)
    return OSC_EPOCH + td
    
def datetime_to_timetag_value(dt):
    td = dt - OSC_EPOCH
    return seconds_from_timedelta(td)
    
def pack_args(value):
    if isinstance(value, list) or isinstance(value, tuple):
        return value
    elif value is None:
        return []
    return [value]

class OSCNode(BaseObject):
    _Properties = {'name':dict(default=''), 
                   'children':dict(type=dict)}
    def __init__(self, **kwargs):
        super(OSCNode, self).__init__(**kwargs)
        self.register_signal('message_received', 'message_not_dispatched')
        self.parent = kwargs.get('parent')
        self.is_root_node = kwargs.get('root_node', False)
        self.bind(name=self._on_name_set)
        self.name = kwargs.get('name')
        if self.name is None or not len(self.name):
            self.name = str(id(self))
        if self.is_root_node:
            self.debug = self.GLOBAL_CONFIG.get('arg_parse_dict', {}).get('debug_osc')
            self._oscMaster = kwargs.get('oscMaster', False)
            self.get_client_cb = kwargs.get('get_client_cb')
            self.transmit_callback = kwargs.get('transmit_callback')
            self.get_epoch_offset_cb = kwargs.get('get_epoch_offset_cb')
            self._dispatch_thread = OSCDispatchThread(osc_tree=self)
            self._dispatch_thread.start()
        else:
            self.get_client_cb = self.parent.get_client_cb
            self._oscMaster = self.parent._oscMaster
        
    @property
    def oscMaster(self):
        return self._oscMaster
    @oscMaster.setter
    def oscMaster(self, value):
        if value != self.oscMaster:
            self.get_root_node()._set_oscMaster(value)
    @property
    def dispatch_thread(self):
        return self.get_root_node()._dispatch_thread
    def _on_name_set(self, **kwargs):
        old = kwargs.get('old')
        value = kwargs.get('value')
        if not self.parent:
            return
        if old in self.parent.children:
            del self.parent.children[old]
        self.parent.children[value] = self
        #print 'name changed: old=%s, new=%s, result=%s' % (old, value, value in self.parent.children)
    def _set_oscMaster(self, value):
        self._oscMaster = value
        for child in self.children.itervalues():
            child._set_oscMaster(value)
    def add_child(self, **kwargs):
        name = kwargs.get('name')
        address = kwargs.get('address', '')
        if len(address) and address[0] == '/':
            if not self.is_root_node:
                return self.get_root_node().add_child(**kwargs)
        parent = kwargs.get('parent', self)
        def do_add_node(**nkwargs):
            nkwargs.setdefault('parent', self)
            new_node = OSCNode(**nkwargs)
            #print 'new_node: parent=%s, name=%s, root=%s' % (self.name, new_node.name, new_node.is_root_node)
            #self.children[new_node.name] = new_node
            new_node.bind(children=self.on_childnode_children_update)
            return new_node
        if parent != self:
            return parent.add_child(**kwargs)
        if not isinstance(address, Address):
            address = Address(address)
        if name is not None:
            address = address.append(name)
        #print address
        #elif 'name' in kwargs:
        #    address = Address(name)
        current, address = address.pop()
        #print 'current=%s, address=%s' % (current, address)
        node = self.children.get(current)
        if not node:
            node = do_add_node(name=current)
        if not len(address.split()):
            return node
        return node.add_child(address=address)
        
    def unlink(self):
        if not self.is_root_node:
            for key in self.children.keys()[:]:
                self.remove_node(name=key)
        super(OSCNode, self).unlink()
        
    def remove_node(self, **kwargs):
        name = kwargs.get('name')
#        address = kwargs.get('address', '')
#        if not isinstance(address, Address):
#            address = Address(address)
#        if name is not None:
#            address = address.append(name)
#        current, address = address.pop()
        current = name
        node = self.children.get(current)
        if not node:
            return False
        #result = node.remove_node(address=address)
        
        if True:#result:
            node.unlink()
            node.unbind(self)
            del self.children[node.name]
        if not len(self.children):
            return True
            
    def unlink_all(self, direction='up', blocking=False):
        self.unlink()
        if self.is_root_node:
            self._dispatch_thread.stop(blocking=blocking)
        if direction == 'up' and not self.is_root_node:
            self.parent.unlink_all(direction, blocking)
        elif direction == 'down':
            for c in self.children.itervalues():
                c.unlink_all(direction, blocking)
                
    def on_childnode_children_update(self, **kwargs):
        pass
    def get_full_path(self, address=None):
        if address is None:
            address = Address(self.name)
        else:
            address = address.append_right(self.name)
        if self.is_root_node:
            #print 'full path: ', address
            return address
        return self.parent.get_full_path(address)
        
    def get_root_node(self):
        if self.is_root_node:
            return self
        return self.parent.get_root_node()
        
    def match_address(self, address):
        if not isinstance(address, Address):
            address = Address(address)
        if self.is_root_node:
            current, address = address.pop()
        #print self.name, ' match: ', address
        current, address = address.pop()
        if not len(current):
            return set([self])
        matched = set()
        nodes = set()
        node = self.children.get(current)
        if node:
            nodes.add(node)
        nodes |= self.match_wildcard(current)
        for node in nodes:
            matched |= node.match_address(address)
        return matched
        
    def match_wildcard(self, s):
        #print self.name, ' match wildcard ', s
        matched = set()
        children = self.children
        #if not len(set('*?[]{}') & set(s)):
        #    return matched
        if '*' in s:
            matched |= set(children.keys())
        elif '{' in s:
            keys = s.strip('{').strip('}').split(',')
            print 'matching {} wildcard: %s, keys=%s' % (s, keys)
            matched |= set(keys) & set(children.keys())
        for key in children.iterkeys():
            if not len(set('*?[]{}') & set(key)):
                continue
            if '*' in key:
                matched.add(key)
            elif '{' in key:
                if s in key:
                    matched.add(key)
        return set([children[key] for key in matched])
            
        
    def dispatch_message(self, **kwargs):
        if not self.is_root_node:
            self.get_root_node().dispatch_message(**kwargs)
            return
        element = kwargs.get('element')
        data = kwargs.get('data')
        client = kwargs.get('client')
        timestamp = kwargs.get('timestamp')
        if data:
            element = parse_message(data, client=client, timestamp=timestamp)
        if self.debug:
            self.LOG.info('osc recv: ' + str(element))
        if isinstance(element, Bundle) and element.timetag > 0:
            self.dispatch_thread.add_bundle(element)
        else:
            self._do_dispatch_message(element)
            
    def _do_dispatch_message(self, element):
        if isinstance(element, Bundle):
            m = element.get_messages()
        else:
            m = [element]
        for msg in m:
            matched = self.match_address(msg.address)
            for node in matched:
                #print 'dispatching msg: ', msg.address, msg.get_arguments(), '(from %s)' % msg.client.name
                node.emit('message_received', message=msg, client=msg.client)
            if not len(matched):
                self.emit('message_not_dispatched', message=msg, client=msg.client)
                self.LOG.info('OSC msg not dispatched: ', msg.address, msg.get_arguments(), self.children.keys(), msg.client.name)
            
    def send_message(self, **kwargs):
        if 'full_path' not in kwargs:
            address = kwargs.get('address')
            full_path = self.get_full_path()
            if address is not None:
                if not isinstance(address, Address):
                    address = Address(address)
                full_path = full_path.append(address)
                del kwargs['address']
            kwargs['full_path'] = full_path
        if not self.is_root_node:
            self.get_root_node().send_message(**kwargs)
            return
        timetag = kwargs.get('timetag')
        if timetag is None:
            now = datetime.datetime.now()
            offset = self.get_epoch_offset_cb()
            timetag = datetime_to_timetag_value(now - offset)
        ## TODO: figure out what's wrong with timetags
        timetag = -1
        value = pack_args(kwargs.get('value'))
        message = Message(*value, address=kwargs['full_path'])
        bundle = Bundle(message, timetag=timetag)
        kwargs['element'] = bundle
        self.transmit_callback(**kwargs)
        
        

def get_ui_module(name):
    if name == 'kivy':
        from kivy.clock import Clock
        return Clock
    elif name == 'gtk':
        return None
    t = imp.find_module(name)
    module = imp.load_module(name, *t)
    return module

## TODO: make this use the threadbases.BaseThread class
class OSCDispatchThread(threading.Thread):
    _ui_mode_dispatch_methods = {'gtk':'gtk_do_dispatch', 
                                 'kivy':'kivy_do_dispatch'}
    def __init__(self, **kwargs):
        threading.Thread.__init__(self)
        self.running = threading.Event()
        self.ready_to_dispatch = threading.Event()
        self.LOG = BaseObject().LOG
        self.bundles = {}
        self.osc_tree = kwargs.get('osc_tree')
        self.do_dispatch = self._do_dispatch
        self.ui_module = None
        self.kivy_messengers = set()
        ui = self.osc_tree.GLOBAL_CONFIG.get('ui_mode')
        if ui is not None and ui != 'text':
            self.ui_module = get_ui_module(ui)
            attr = self._ui_mode_dispatch_methods.get(ui)
            if attr:
                self.do_dispatch = getattr(self, attr)
        
    def add_bundle(self, bundle):
        dt = bundle.timetag.datetime
        if dt in self.bundles:
            dt = dt + datetime.timedelta(microseconds=1)
        self.bundles[dt] = bundle
        self.ready_to_dispatch.set()
        
    def get_next_datetime(self):
        if len(self.bundles):
            return min(self.bundles.keys())
        return False
        
    def run(self):
        self.running.set()
        while self.running.isSet():
            self.ready_to_dispatch.wait()
            if not self.running.isSet():
                return
            dt = self.get_next_datetime()
            if dt is False:
                self.ready_to_dispatch.clear()
            else:
                now = datetime.datetime.now()
                offset = self.osc_tree.get_epoch_offset_cb()
                now = now + offset
                if dt <= now:
                    bundle = self.bundles[dt]
                    del self.bundles[dt]
                    messages = bundle.get_messages()
                    try:
                        self.do_dispatch(messages)
                    except:
                        self.LOG.warning(sys.exc_info())
                else:
                    self.ready_to_dispatch.clear()
                    timeout = seconds_from_timedelta(dt - now)
                    self.ready_to_dispatch.wait(timeout)
                    self.ready_to_dispatch.set()
                    
    def _do_dispatch(self, messages):
        for m in messages:
            self.osc_tree._do_dispatch_message(m)
            
    def gtk_do_dispatch(self, messages):
        #self.ui_module.gdk.threads_enter()
        self._do_dispatch(messages)
        #self.ui_module.gdk.threads_leave()
                
    def kivy_do_dispatch(self, messages):
        obj = Messenger(messages=messages, callback=self._on_kivy_msg_cb)
        self.kivy_messengers.add(obj)
        self.ui_module.schedule_once(obj.send, 0)
        
    def _on_kivy_msg_cb(self, messenger):
        self._do_dispatch(messenger.messages)
        self.kivy_messengers.discard(messenger)

    def stop(self, **kwargs):
        blocking = kwargs.get('blocking')
        self.running.clear()
        self.ready_to_dispatch.set()
        if blocking and self.isAlive():
            self.join()

class Messenger(object):
    __slots__ = ('messages', 'callback', '__weakref__')
    def __init__(self, **kwargs):
        for key, val in kwargs.iteritems():
            setattr(self, key, val)
    def send(self, *args):
        self.callback(self)
        
if __name__ == '__main__':
    td = datetime.timedelta()
    def get_client(*args, **kwargs):
        pass
    def get_epoch(*args, **kwargs):
        return td
    def transmit(*args, **kwargs):
        element = kwargs.get('element')
        print str(element)
        e2 = parse_message(element.build_string())
        print [element.build_string()]
        print str(e2)
        root.dispatch_message(data=element.build_string())
    root = OSCNode(name='root', 
                   root_node=True, 
                   get_client_cb=get_client, 
                   get_epoch_offset_cb=get_epoch, 
                   transmit_callback=transmit)
    tail = root.add_child(address='blah/stuff/things')
    print tail.get_full_path()
    tail.send_message(value=[1, True, 'a'])
    print root.match_address('/root/blah/stuff/things')
