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
                self.LOG.info(self.address, 'callback removed', key)
                del self.callbacks[key]
            except:
                self.LOG.warning(self.address, 'could not remove callback', key)
            
    def handle_message(self, message, hostaddr):
        address = message.address
        method = address.split('/')[-1:][0]
        #print 'received: address=%s, method=%s, args=%s' % (address, method, message.getValues())
        cb_kwargs = dict(method=method, address=address, values=message.getValues())
        if self.osc_node.get_client_cb:
            cb_kwargs['client'] = self.osc_node.get_client_cb(hostaddr=hostaddr)
        else:
            self.LOG.warning(self, 'no callback!!!!')
        if method in self.callbacks:
            #print 'osc_callback: ', address, message.getValues()
            self.callbacks[method](**cb_kwargs)
        elif '*' in ''.join(self.callbacks.keys()):
            for key, cb in self.callbacks.iteritems():
                if '*' in key:
                    cb(**cb_kwargs)
        else:
            self.LOG.warning('msg not handled: cb_kwargs = ', cb_kwargs)
            
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