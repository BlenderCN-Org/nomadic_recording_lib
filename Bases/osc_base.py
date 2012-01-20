#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# osc_base.py
# Copyright (c) 2010 - 2011 Matthew Reid

import sys
import threading
import imp
import datetime
import math
import struct

from txosc import dispatch, osc

from BaseObject import BaseObject
from Properties import PropertyConnector

def join_address(*args):
    s = '/'.join(['/'.join(arg.split('/')) for arg in args])
    return s
    
def pack_args(value):
    if isinstance(value, list) or isinstance(value, tuple):
        return value
    elif value is None:
        return []
    return [value]
    
def get_node_path(node):
    parent = node
    path = []
    while parent is not None:
        path.append(parent._name)
        parent = parent._parent
    path.reverse()
    return join_address(*path)

class OSCBaseObject(BaseObject):
    _saved_attributes = ['osc_address']
    def __init__(self, **kwargs):
        self.osc_enabled = False
        address = kwargs.get('osc_address')
        if address is None and hasattr(self, 'osc_address'):
            address = getattr(self, 'osc_address')
        if address is not None:
            self.osc_address = str(address)
        parent = kwargs.get('osc_parent_node')
        if parent is None and hasattr(self, 'osc_parent_node'):
            parent = getattr(self, 'osc_parent_node')
        if parent is not None:
            self.osc_parent_node = parent
        self.osc_enabled = parent is not None and address is not None
        
        if self.osc_enabled:
            self.osc_handlers = {}
            self.osc_child_nodes = set()
            self.osc_node = self.osc_parent_node.add_new_node(name=self.osc_address)
            self.set_osc_address(self.osc_address)
        else:
            self.osc_address = None
            
        super(OSCBaseObject, self).__init__(**kwargs)
            
    def unlink(self):
        def remove_node(n):
            if n._parent is not None:
                n._parent.removeNode(n._name)
        if self.osc_enabled:
            for handler in self.osc_handlers.itervalues():
                handler.unlink()
                n = handler.osc_node
                if n != self.osc_node:
                    remove_node(n)
            remove_node(self.osc_node)
        super(OSCBaseObject, self).unlink()
        
    def set_osc_address(self, address):
        if not self.osc_enabled or address is None:
            return
        for c in ['/', ' ']:
            if c in address:
                address = '_'.join(address.split(c))
        self.osc_address = address
        self.osc_node.setName(address)
            
    def add_osc_child(self, **kwargs):
        if self.osc_enabled:
            address = kwargs.get('address')
            d = {'osc_address':address, 'osc_parent_node':self.osc_node}
            return d
        return {}
        
    def add_osc_handler(self, **kwargs):
        '''Add an OSC handler
        :Parameters:
            'address' : Relative address to self.osc_node. Default is
                        None which will use the address of self.osc_node
            'callbacks' : Dict of {'address':callback} to handle. Default is None
                          which disables callback mode and requires parameters below.
            'Property' : links a Property object to the osc handler so you don't have
                         to do anything yourself anymore (uses PropertyConnector).
                         give it a Property object or string of the Property name.
            'request_initial_value' : bool
        '''
        if not self.osc_enabled:
            return
        
        address = kwargs.get('address')
        Property = kwargs.get('Property')
        all_sessions = kwargs.get('all_sessions', False)
        if Property is not None:
            if type(Property) == str:
                Property = self.Properties[Property]
                kwargs['Property'] = Property
            address = Property.name
        
        
        if address is None:
            node = self.osc_node
            address = self.osc_address
            kwargs['address'] = address
        else:
            node = self.osc_node.add_new_node(name=address)
        kwargs.setdefault('osc_node', node)
        
        objhandler = self.osc_handlers.get(address)
        if not objhandler:
            objhandler = OSCHandler(**kwargs)
            self.osc_handlers.update({address:objhandler})
        else:
            objhandler.add_callbacks(**kwargs.get('callbacks', {}))
        return objhandler
            
    def remove_osc_handler(self, **kwargs):
        key = kwargs.get('id')
        if key in self.osc_handlers:
            self.osc_handlers[key].remove_callbacks()
            del self.osc_handlers[key]
    

class OSCHandler(BaseObject, PropertyConnector):
    def __init__(self, **kwargs):
        super(OSCHandler, self).__init__()
        self.callbacks = {}
        self.request_initial_value = kwargs.get('request_initial_value')
        self.address = kwargs.get('address')
        #self.callbacks = kwargs.get('callbacks')
        self.osc_node = kwargs.get('osc_node')
        #self.osc_node.addCallback(self.address+'/*', self.handle_message)
        callbacks = kwargs.get('callbacks', {})
        self.add_callbacks(**callbacks)
        self.send_root_address = kwargs.get('send_root_address')
        self.send_client = kwargs.get('send_client')
        self.all_sessions = kwargs.get('all_sessions', False)
        self.Property = kwargs.get('Property')
        
    def unlink(self):
        self.Property = None
        #self.remove_callbacks()
        super(OSCHandler, self).unlink()
        
    def add_callbacks(self, **kwargs):
        self.callbacks.update(kwargs)
        for key in kwargs.iterkeys():
            self.osc_node.addCallback('%s/%s' % (self.address, key), self.handle_message)
            #print self.osc_node._name, '%s/%s' % (self.address, key)
            
    def remove_callbacks(self):
        for key in self.callbacks.keys()[:]:
            try:
                self.osc_node.removeCallback('%s/%s' % (self.address, key), self.handle_message)
                #print self.address, ' callback removed: ', key
                del self.callbacks[key]
            except:
                pass
                #print self.address, ' could not remove callback: ', key
            
    def handle_message(self, message, hostaddr):
        address = message.address
        method = address.split('/')[-1:][0]
        #print 'received: address=%s, method=%s, args=%s' % (address, method, message.getValues())
        cb_kwargs = dict(method=method, address=address, values=message.getValues())
        if self.osc_node.get_client_cb:
            cb_kwargs['client'] = self.osc_node.get_client_cb(hostaddr=hostaddr)
        else:
            pass
            #print 'no callback!!!!'
        if method in self.callbacks:
            #print 'osc_callback: ', address, message.getValues()
            self.callbacks[method](**cb_kwargs)
        elif '*' in ''.join(self.callbacks.keys()):
            for key, cb in self.callbacks.iteritems():
                if '*' in key:
                    cb(**cb_kwargs)
        else:
            #print 'msg not handled: cb_kwargs = ', cb_kwargs
            pass
                    
    def send_methods(self):
        pass
        
    def attach_Property(self, prop):
        super(OSCHandler, self).attach_Property(prop)
        self.Property_set_by_osc = False
        self.add_callbacks(**{'set-value':self.on_osc_Property_value_changed, 
                              'current-value':self.on_osc_Property_value_requested})
        if not self.osc_node.oscMaster and self.request_initial_value:
            self.request_Property_value()
                
    def on_Property_value_changed(self, **kwargs):
        self.send_Property_value_to_osc()
        
    def send_Property_value_to_osc(self, **kwargs):
        if self.Property_set_by_osc:
            #self.Property_set_by_osc = False
            return
        value = self.get_Property_value()
        if isinstance(value, dict):
            args = []
            for key, val in value.iteritems():
                args.extend([key, val])
        elif isinstance(value, list):
            args = value
        else:
            args = [value]
        msg_kwargs = dict(value=args, address=kwargs.get('address', 'set-value'), all_sessions=self.all_sessions)
        if 'client' in kwargs:
            msg_kwargs['client'] = kwargs['client']
        elif self.send_client is not None:
            msg_kwargs['client'] = self.send_client
        if self.send_root_address is not None:
            msg_kwargs['root_address'] = self.send_root_address
        #print msg_kwargs
        self.osc_node.send_message(**msg_kwargs)
            
    def on_osc_Property_value_changed(self, **kwargs):
        args = kwargs.get('values')
        ptype = self.Property._type
        if ptype is not None:
            if issubclass(ptype, dict):
                ## make sure there's an even number of arguments
                if not len(args) or len(args) % 2 != 0:
                    return
                keys = [args[i] for i in range(0, len(args), 2)]
                vals = [args[i] for i in range(1, len(args), 2)]
                value = dict(zip(keys, vals))
            elif issubclass(ptype, list):
                value = args
            else:
                return
        else:
            value = args[0]
        self.Property_set_by_osc = True
        self.set_Property_value(value)
        self.Property_set_by_osc = False
                
    def on_osc_Property_value_requested(self, **kwargs):
        self.send_Property_value_to_osc(client=kwargs.get('client').name, all_sessions=self.all_sessions)
        
    def request_Property_value(self, **kwargs):
        kwargs.update(dict(address='current-value', all_sessions=self.all_sessions))
        self.osc_node.send_message(**kwargs)

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
    
    

class OSCNode(BaseObject, dispatch.Receiver):
    _saved_class_name = 'OSCNode'
    _saved_child_objects = ['_childNodes']
    def __init__(self, **kwargs):
        #super(OSCNode, self).__init__()
        BaseObject.__init__(self, **kwargs)
        dispatch.Receiver.__init__(self)
        self.register_signal('child_added', 'child_removed')
        
        if 'name' in kwargs:
            self.setName(kwargs.get('name'))
        if 'parent' in kwargs:
            self.setParent(kwargs.get('parent'))
            self._oscMaster = self._parent._oscMaster
            self.get_client_cb = self._parent.get_client_cb
        else:
            self._oscMaster = kwargs.get('oscMaster', False)
            self.get_client_cb = kwargs.get('get_client_cb')
        self.is_root_node = kwargs.get('root_node', False)
        self.transmit_callback = kwargs.get('transmit_callback')
        if self.is_root_node:
            self.get_epoch_offset_cb = kwargs.get('get_epoch_offset_cb')
            self._dispatch_thread = OSCDispatchThread(osc_tree=self)
            self._dispatch_thread.start()
        
    def unlink(self):
#        for c in self._childNodes.itervalues():
#            if not isinstance(c, OSCNode):
#                continue
#            #c.unlink()
#            c.unbind(self)
        super(OSCNode, self).unlink()
        
    def unlink_all(self, direction='up', blocking=False):
        self.unlink()
        if self.is_root_node:
            self._dispatch_thread.stop(blocking=blocking)
        if direction == 'up' and not self.is_root_node:
            self._parent.unlink_all(direction, blocking)
        elif direction == 'down':
            for c in self._childNodes.itervalues():
                c.unlink_all(direction, blocking)
        
        
    @property
    def oscMaster(self):
        return self._oscMaster
    @oscMaster.setter
    def oscMaster(self, value):
        if value != self.oscMaster:
            self.get_root_node()._set_oscMaster(value)
            
    @property
    def epoch(self):
        return OSC_EPOCH
        
    @property
    def dispatch_thread(self):
        return self.get_root_node()._dispatch_thread
        
    def setName(self, newname):
        """
        Give this node a new name.
        @type newname: C{str}
        """
        p = self._parent
        if p and self._name in p._childNodes:
            del p._childNodes[self._name]
        self._name = newname
        if self._parent:
            self._parent._childNodes[self._name] = self
        
    def _set_oscMaster(self, value):
        self._oscMaster = value
        for child in self._childNodes.itervalues():
            child._set_oscMaster(value)
        
    def add_new_node(self, **kwargs):
        name = kwargs.get('name')
        address = kwargs.get('address')
        parent = kwargs.get('parent', self)
        if parent == self:
            if address:
                path = self._patternPath(address)
                nodes = self.search_nodes(path)
                node = self
                if nodes:
                    i = len(nodes) - 1
                    if nodes[i] == True:
                        return nodes[i-1]
                    node = nodes[i-1]
                    path = path[i:]
                    
                for s in path[1:]:
                    node = node.add_new_node(name=s)
                return node
            if name in self._childNodes:
                return self._childNodes[name]
            new_node = OSCNode(name=name, parent=self)
            new_node.bind(child_added=self._on_childNode_child_added, 
                          child_removed=self._on_childNode_child_removed)
            self.emit('child_added', node=self, name=name)
            return new_node
        if self._parent is not None:
            return self._parent.add_new_node(**kwargs)
        return None
        
    def search_nodes(self, path, index=0, result=None):
        if result is None:
            result = []
        if index != 0:
            result.append(self)
        if index >= len(path)-1:
            if path[index] == self._name:
                result.append(True)
            else:
                result.append(False)
            return result
        index += 1
        child = self._childNodes.get(path[index])
        if child:
            child.search_nodes(path, index, result)
        else:
            if result and result[len(result)-1] != True:
                result.append(False)
        return result
            
        
    def send_message(self, **kwargs):
        '''Send an OSC message object up through the tree and finally
        out of the root node
        :Parameters:
            'address' : relative OSC address from the node that is sending
            'value' : OSC args to send, can be list, tuple or single value
                        of any type supported by OSC
        '''
        if self.is_root_node:
            now = datetime.datetime.now()
            offset = self.get_epoch_offset_cb()
            kwargs['timetag'] = datetime_to_timetag_value(now - offset)
            self.transmit_callback(**kwargs)
            return
        address = kwargs.get('address')
        if type(address) == str:
            address = [address]
        address[0:0] = [self._name]
        kwargs['address'] = address
        self._parent.send_message(**kwargs)
        
    def get_full_path(self, address=None):
        if self.is_root_node:
            return address
        if address is None:
            address = []
        address[0:0] = [self._name]
        return self._parent.get_full_path(address)
        
    def get_root_node(self):
        if self.is_root_node:
            return self
        return self._parent.get_root_node()
        
    def addNode(self, name, instance):
        super(OSCNode, self).addNode(name, OSCNode())
        self._childNodes[name].bind(child_added=self._on_childNode_child_added, 
                                    child_removed=self._on_childNode_child_removed)
        self.emit('child_added', node=self, name=name)
        
    def removeNode(self, name):
        node = self._childNodes.get(name)
        if not node:
            return False
        for cname in node._childNodes.keys()[:]:
            node.removeNode(cname)
        node.removeCallbacks()
        
            #node.removeAllCallbacks()
        #node.unbind(self)
        #print 'removeNode: ', self, name
        #node.removeCallbacks()
        
    def _checkRemove(self):
        has_parent = self._parent is not None
        if has_parent and self._name in self._parent._childNodes:
            dispatch.Receiver._checkRemove(self)
        if has_parent and self._name not in self._parent._childNodes:
            #self._parent.unbind(self)
            #self.unlink()
            self._parent.emit('child_removed', node=self._parent, name=self._name)
            
    def _on_childNode_child_added(self, **kwargs):
        #if not self._parent:
        #    return
        #print self, 'added', kwargs
        self.emit('child_added', **kwargs)
        
    def _on_childNode_child_removed(self, **kwargs):
        #if not self._parent:
        #    return
        #print self, 'removed', kwargs
        self.emit('child_removed', **kwargs)
    
    def dispatch(self, element, client):
        if isinstance(element, osc.Bundle):
            self.dispatch_thread.add_bundle(element, client)
        else:
            #try:
            super(OSCNode, self).dispatch(element, client)
            #except:
            #    print 'could not dispatch stuff:\n%s\n%s %s' % (sys.exc_info(), element.address, element.getValues())
            

class Bundle(osc.Bundle):
    def toBinary(self):
        """
        Encodes the L{Bundle} to binary form, ready to send over the wire.

        @return: A string with the binary presentation of this L{Bundle}.
        """
        data = osc.StringArgument("#bundle").toBinary()
        data += TimeTagArgument(self.timeTag).toBinary()
        for msg in self.elements:
            binary = msg.toBinary()
            data += osc.IntArgument(len(binary)).toBinary()
            data += binary
        return data
    
    @staticmethod
    def fromBinary(data):
        """
        Creates a L{Bundle} object from binary data that is passed to it.

        This static method is a factory for L{Bundle} objects.

        @param data: String of bytes formatted following the OSC protocol.
        @return: Two-item tuple with L{Bundle} as the first item, and the
        leftover binary data, as a L{str}. That leftover should be an empty string.
        """
        bundleStart, data = osc._stringFromBinary(data)
        if bundleStart != "#bundle":
            raise osc.OscError("Error parsing bundle string")
        saved_data = data[:]
        bundle = Bundle()
        try:
            bundle.timeTag, data = TimeTagArgument.fromBinary(data)
            while data:
                size, data = osc.IntArgument.fromBinary(data)
                size = size.value
                if len(data) < size:
                    raise osc.OscError("Unexpected end of bundle: need %d bytes of data" % size)
                payload = data[:size]
                bundle.elements.append(_elementFromBinary(payload))
                data = data[size:]
            return bundle, ""
        except osc.OscError:
            data = saved_data
            bundle.timeTag, data = osc.TimeTagArgument.fromBinary(data)
            while data:
                size, data = osc.IntArgument.fromBinary(data)
                size = size.value
                if len(data) < size:
                    raise osc.OscError("Unexpected end of bundle: need %d bytes of data" % size)
                payload = data[:size]
                bundle.elements.append(_elementFromBinary(payload))
                data = data[size:]
            return bundle, ""
    
class TimeTagArgument(osc.Argument):
    typeTag = "t"

    def __init__(self, value=True):
        osc.Argument.__init__(self, value)

    def toBinary(self):
        if self.value is True:
            return struct.pack('>qq', 0, 1)
        fr, sec = math.modf(self.value)
        return struct.pack('>qq', long(sec), long(fr * 1e9))
        
    @staticmethod
    def fromBinary(data):
        binary = data[0:16]
        if len(binary) != 16:
            raise osc.OscError("Too few bytes left to get a timetag from %s." % (data))
        leftover = data[16:]

        if binary == '\0\0\0\0\0\0\0\1':
            # immediately
            time = True
        else:
            high, low = struct.unpack(">qq", data[0:16])
            time = float(int(high) + low / float(1e9))
        return TimeTagArgument(time), leftover

def _elementFromBinary(data):
    if data[0] == "/":
        element, data = osc.Message.fromBinary(data)
    elif data[0] == "#":
        element, data = Bundle.fromBinary(data)
    else:
        raise osc.OscError("Error parsing OSC data: " + data)
    return element

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
        
    def add_bundle(self, bundle, client):
        tt = bundle.timeTag
        if tt is not None:
            dt = timetag_to_datetime(timetag_obj=tt)
        else:
            dt = datetime.datetime.now()
        self.bundles[dt] = (bundle, client)
        self.ready_to_dispatch.set()
        
    def get_next_datetime(self):
        if len(self.bundles):
            keys = self.bundles.keys()
            keys.sort()
            return keys[0]
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
                    bundle, client = self.bundles[dt]
                    del self.bundles[dt]
                    messages = bundle.getMessages()
                    try:
                        self.do_dispatch(messages, client)
                    except:
                        pass
                else:
                    self.ready_to_dispatch.clear()
                    timeout = seconds_from_timedelta(dt - now)
                    self.ready_to_dispatch.wait(timeout)
                    self.ready_to_dispatch.set()
                    
    def _do_dispatch(self, messages, client):
        for m in messages:
            self.osc_tree.dispatch(m, client)
            
    def gtk_do_dispatch(self, messages, client):
        #self.ui_module.gdk.threads_enter()
        self._do_dispatch(messages, client)
        #self.ui_module.gdk.threads_leave()
                
    def kivy_do_dispatch(self, messages, client):
        obj = Messenger(messages=messages, client=client, callback=self._on_kivy_msg_cb)
        self.kivy_messengers.add(obj)
        self.ui_module.schedule_once(obj.send, 0)
        
    def _on_kivy_msg_cb(self, messenger):
        self._do_dispatch(messenger.messages, messenger.client)
        self.kivy_messengers.discard(messenger)

    def stop(self, **kwargs):
        blocking = kwargs.get('blocking')
        self.running.clear()
        self.ready_to_dispatch.set()
        if blocking and self.isAlive():
            self.join()

class Messenger(object):
    __slots__ = ('messages', 'client', 'callback', '__weakref__')
    def __init__(self, **kwargs):
        for key, val in kwargs.iteritems():
            setattr(self, key, val)
    def send(self, *args):
        self.callback(self)
