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
# oscmanager.py
# Copyright (c) 2011 Matthew Reid

import threading
import time
import datetime
import socket

#from txosc import osc
#from Bases.osc_node import OSCNode, Bundle
from Bases import BaseObject, OSCBaseObject, BaseThread, Config

from .. import BaseIO

from messages import Message, Bundle, Address
from osc_node import OSCNode
from osc_io import oscIO
from osc_client import Client


def join_address(*args):
    s = '/'.join(['/'.join(arg.split('/')) for arg in args])
    return s
    
def issequence(obj):
    for t in [list, tuple, set]:
        if isinstance(obj, t):
            return True
    return False
    

class OSCManager(BaseIO.BaseIO, Config):
    _confsection = 'OSC'
    _Properties = {'app_address':dict(type=str), 
                   'master_priority':dict(default=10), 
                   'session_name':dict(type=str), 
                   'discovered_sessions':dict(default={}), 
                   'ring_master':dict(type=str)}
    def __init__(self, **kwargs):
        self.comm = kwargs.get('comm')
        BaseIO.BaseIO.__init__(self, **kwargs)
        Config.__init__(self, **kwargs)
        self.register_signal('client_added', 'client_removed', 'unique_address_changed', 'new_master')
        self.app_address = self.GLOBAL_CONFIG.get('app_name', self.get_conf('app_address', 'OSCApp'))
        self.default_root_address = kwargs.get('root_address', '%s-%s' % (self.app_address, socket.gethostname()))
        self.root_address = self.default_root_address
        self.wildcard_address = None
        self.master_priority = int(self.get_conf('master_priority', 10))
        self.GLOBAL_CONFIG['master_priority'] = self.master_priority
        s = self.GLOBAL_CONFIG.get('session_name')
        if s is not None:
            self.session_name = s
        else:
            self.session_name = socket.gethostname()
            self.GLOBAL_CONFIG['session_name'] = self.session_name
        self.osc_tree = OSCNode(name=self.app_address, 
                                root_node=True, 
                                transmit_callback=self.on_node_tree_send, 
                                get_client_cb=self.get_client, 
                                get_epoch_offset_cb=self.get_epoch_offset)
        #self.root_node = self.osc_tree.add_child(name=self.app_address)
        self.root_node = self.osc_tree
        #self.epoch_offset = datetime.timedelta()
        self.epoch_offset = 0.
        self.clock_send_thread = None
        s = kwargs.get('use_unique_addresses', self.get_conf('use_unique_addresses', 'True'))
        flag = not s == 'False'
        
        #self.root_node.addCallback('/clocksync', self.on_master_sent_clocksync)
        csnode = self.root_node.add_child(name='clocksync')
        csnode.bind(message_received=self.on_master_sent_clocksync)
        self.clocksync_node = csnode
        self.ioManager = oscIO(Manager=self)
        self.SessionManager = OSCSessionManager(Manager=self)
        self.SessionManager.bind(client_added=self.on_client_added, 
                                 client_removed=self.on_client_removed, 
                                 new_master=self.on_new_master)
        self.set_use_unique_address(flag, update_conf=False)
        io = kwargs.get('connection_type', self.get_conf('connection_type', 'Multicast'))
        self.ioManager.build_io(iotype=io, update_conf=False)
        
    @property
    def oscMaster(self):
        return self.SessionManager.oscMaster
    @property
    def isMaster(self):
        return self.SessionManager.isMaster
    @property
    def isRingMaster(self):
        return self.SessionManager.isRingMaster
    @property
    def clients(self):
        return self.SessionManager.clients
    @property
    def local_client(self):
        return self.SessionManager.local_client
        
    def get_epoch_offset(self):
        return self.epoch_offset
        
    def do_connect(self, **kwargs):
        self.SessionManager.do_connect()
        self.ioManager.do_connect(**kwargs)
        self.connected = True
        
    def do_disconnect(self, **kwargs):
        self.stop_clock_send_thread(blocking=True)
        self.ioManager.do_disconnect(**kwargs)
        self.SessionManager.do_disconnect(**kwargs)
        self.connected = False
        
    def shutdown(self):
        self.do_disconnect(blocking=True)
        self.osc_tree.unlink_all(direction='down', blocking=True)
        
        
    def set_use_unique_address(self, flag, update_conf=True):
        self.use_unique_address = flag
        if update_conf:
            self.update_conf(use_unique_addresses=flag)
        self.set_address_vars()
        self.emit('unique_address_changed', state=flag)
    
    def set_address_vars(self):
        return
        if self.ioManager.iotype == 'Multicast' or self.use_unique_address:
            self.root_address = self.default_root_address
            #self.SessionManager.add_client_name(None, update_conf=False)
        else:
            self.root_address = self.app_address
            self.root_node.name = self.root_address
            
    def update_wildcards(self):
        return
        #if self.wildcard_address:
        #    self.osc_tree._wildcardNodes.discard(self.wildcard_address)
        #    self.osc_tree._wildcardNodes.discard('{null}')
        names = []
        for c in self.clients.itervalues():
            if not c.isLocalhost:
                names.append(c.osc_name)
        if names:
            s = '{%s}' % (','.join(names))
            self.wildcard_address = s
            self.root_node.name = s
            #self.osc_tree._wildcardNodes.add(s)
            #print 'wildcard = ', s
            #print 'root_node = ', s
            #print 'wcnodes = ', self.osc_tree._wildcardNodes
        
    def get_client(self, **kwargs):
        hostaddr = kwargs.get('hostaddr')[0]
        #print hostaddr, self.clients_by_address
        return self.SessionManager.clients_by_address.get(hostaddr)
        
    def on_node_tree_send(self, **kwargs):
        clients = kwargs.get('clients')
        client_name = kwargs.get('client')
        element = kwargs.get('element')
#        timetag = kwargs.get('timetag')
#        if timetag is not None:
#            del kwargs['timetag']
        to_master = kwargs.get('to_master', client_name is None and not self.isMaster)
        if to_master:
            client_name = self.oscMaster
        if clients is None:
            client = self.clients.get(client_name)
            if client is not None:
                clients = [client]
#        address = kwargs.get('address')
#        #root_address = kwargs.get('root_address', self.root_address)
        all_sessions = kwargs.get('all_sessions', False)
#        #address[0] = root_address
#        if not isinstance(address, Address):
#            address = Address(address)
#        #junk, address = address.pop()
#        #address = address.append_right(root_address)
#        
#        #path = '/' + join_address(*address)
#        #if path[-1:] == '/':
#        #    path = path[:-1]
#        args = self.pack_args(kwargs.get('value'))
#        msg = Message(*args, address=address)
#        bundle = Bundle(msg, timetag=timetag)
        
        _sender = self.ioManager._sender
        if _sender is None:
            return
        _sender.preprocess(element)
        if isinstance(element, Bundle):
            messages = element.get_flat_messages()
        else:
            messages = [element]
        if self.ioManager.iotype == 'Multicast':
            #print 'osc_send: ', msg
            _sender._send(element)
            return
        if self.ioManager.iotype != 'Unicast':
            return
            
        if clients is None:
            clients = set()
            for c in self.clients.itervalues():
                if all_sessions:
                    if c.sendAllUpdates:
                        clients.add(c)
                else:
                    if c.sendAllUpdates and c.isSameSession:
                        clients.add(c)
        for c in clients:
            if c.accepts_timetags:
                _sender._send(element, c.hostaddr)
            else:
                for msg in messages:
                    _sender._send(msg, c.hostaddr)
    
    def pack_args(self, value):
        if isinstance(value, list) or isinstance(value, tuple):
            return value
        elif value is None:
            return []
        return [value]
        
    def start_clock_send_thread(self):
        self.stop_clock_send_thread()
        self.clock_send_thread = ClockSender(osc_node=self.clocksync_node, 
                                             time_method='timestamp', 
                                             clients=self.clients)
        self.clock_send_thread.start()
        
    def stop_clock_send_thread(self, blocking=True):
        if self.clock_send_thread is None:
            return
        self.clock_send_thread.stop(blocking=blocking)
        self.clock_send_thread = None
            
    def on_master_sent_clocksync(self, **kwargs):
        msg = kwargs.get('message')
        value = msg.get_arguments()[0]
        #dt = datetime.datetime.strptime(value, '%Y%m%d %H:%M:%S %f')
        #now = datetime.datetime.fromtimestamp(msg.timestamp)
        now = time.time()
        #print 'msg.timestamp: ', msg.timestamp
        #tsnow = datetime.datetime.fromtimestamp(msg.timestamp)
        #print 'now=%s, tsnow=%s' % (now, tsnow)
        self.epoch_offset = now - value
        #print 'epoch_offset: ', self.epoch_offset
        
    def on_client_added(self, **kwargs):
        self.emit('client_added', **kwargs)
        
    def on_client_removed(self, **kwargs):
        self.emit('client_removed', **kwargs)
        
    def on_new_master(self, **kwargs):
        self.emit('new_master', **kwargs)
            
class OSCSessionManager(BaseIO.BaseIO, Config):
    _confsection = 'OSC'
    _Properties = {'oscMaster':dict(type=str)}
    def __init__(self, **kwargs):
        self.Manager = kwargs.get('Manager')
        self.ioManager = self.Manager.ioManager
        self.comm = self.Manager.comm
        self.root_node = self.Manager.root_node
        self.osc_tree = self.Manager.osc_tree
        BaseIO.BaseIO.__init__(self, **kwargs)
        Config.__init__(self, **kwargs)
        self.register_signal('client_added', 'client_removed', 'new_master')
        #self.oscMaster = None
        self.bind(oscMaster=self._on_oscMaster_set)
        self.set_master_timeout = None
        self.master_takeover_timer = None
        self.check_master_attempts = None
        self.local_client = None
        self.init_clients()
        #self.root_node.addCallback('/getMaster', self.on_master_requested_by_osc)
        #self.root_node.addCallback('/setMaster', self.on_master_set_by_osc)
        self.getMasterNode = self.root_node.add_child(name='getMaster')
        self.getMasterNode.bind(message_received=self.on_master_requested_by_osc)
        self.setMasterNode = self.root_node.add_child(name='setMaster')
        self.setMasterNode.bind(message_received=self.on_master_set_by_osc)
        self.GLOBAL_CONFIG.bind(update=self.on_GLOBAL_CONFIG_update)
        self.comm.ServiceConnector.connect('new_host', self.on_host_discovered)
        self.comm.ServiceConnector.connect('remove_host', self.on_host_removed)
        
        self.Manager.bind(master_priority=self._on_master_priority_set, 
                          session_name=self._on_session_name_set, 
                          discovered_sessions=self._on_discovered_sessions_set, 
                          ring_master=self._on_ring_master_set)
    
    @property
    def root_address(self):
        return self.Manager.root_address
    @property
    def local_name(self):
        if not self.local_client:
            return '-'.join([self.GLOBAL_CONFIG.get('app_name'), socket.gethostname()])
        return self.local_client.name
    @property
    def isMaster(self):
        return self.oscMaster == self.local_name
    @property
    def isRingMaster(self):
        return self.Manager.ring_master == self.local_name
    @property
    def master_priority(self):
        return self.Manager.master_priority
    @master_priority.setter
    def master_priority(self, value):
        self.Manager.master_priority = value
    @property
    def discovered_sessions(self):
        return self.Manager.discovered_sessions
    @property
    def session_name(self):
        return self.Manager.session_name
    @session_name.setter
    def session_name(self, value):
        self.Manager.session_name = value
        
    def determine_ring_master(self):
        session_masters = {}
        for client in self.clients.itervalues():
            if not client.isMaster:
                continue
            key = int(''.join([s.rjust(3, '0') for s in client.address.split('.')]))
            session_masters[key] = client
        if not len(session_masters):
            return False
        master = session_masters[min(session_masters.keys())]
        if master.name != self.Manager.ring_master:
            self.Manager.ring_master = master.name
        return master
        
        
    def do_connect(self):
        serv = self.comm.ServiceConnector.add_service(**self.build_zeroconf_data())
        self.comm.ServiceConnector.add_listener(stype='_osc._udp')
        self.connected = True
        self.check_for_master()
        
    def do_disconnect(self, **kwargs):
        self.set_master(False)
        self.connected = False
        
    def init_clients(self):
        self.client_osc_node = self.root_node.add_child(name='CLIENTS')
        names = self.get_conf('client_names', ['null'])
        if type(names) == str:
            names = [names]
        self.clients = {}
        self.clients_by_address = {}
        #self.client_names = set(names)
        #self.add_client_name(None, update_conf=False)
        #addresses = self.get_conf('client_addresses', [])
        #if type(addresses) == str:
        #    addresses = [addresses]
        #self.client_addresses = set(addresses)
        #self.add_client_address(None, update_conf=False)
        
    def add_to_session(self, **kwargs):
        name = kwargs.get('name')
        if name is None:
            return
        client = kwargs.get('client')
        clients = kwargs.get('clients', [])
        if client is not None:
            clients.append(client)
        sessions = self.discovered_sessions
        old = sessions.copy()
        session = sessions.get(name, {'clients':set()})
        for client in clients:
            session['clients'].add(client)
            if client.isMaster:
                session['master'] = client
        if name not in sessions:
            sessions[name] = session
        else:
            sessions.parent_property.emit(old)
            
    def remove_from_session(self, **kwargs):
        name = kwargs.get('name')
        client = kwargs.get('client')
        clients = kwargs.get('clients', [])
        if client is not None:
            clients.append(client)
        sessions = self.discovered_sessions
        old = sessions.copy()
        session = sessions.get(name)
        if session is None:
            return
        for client in clients:
            if client == session.get('master'):
                session['master'] = None
            session['clients'].discard(client)
        if not len(sessions[name]['clients']):
            del sessions[name]
        else:
            sessions.parent_property.emit(old)
            
    def add_client(self, **kwargs):
        kwargs.setdefault('port', self.ioManager.hostdata['sendport'])
        kwargs.setdefault('app_address', self.Manager.app_address)
        kwargs['osc_parent_node'] = self.client_osc_node
        if socket.gethostname() in kwargs.get('name', ''):
            kwargs['isLocalhost'] = True
            #kwargs['master_priority'] = self.master_priority
        client = Client(**kwargs)
        self.clients.update({client.name:client})
        self.clients_by_address.update({client.address:client})
        if client.isLocalhost:
            self.local_client = client
            #client.master_priority = self.master_priority
            #print 'local_client session: ', client.session_name
        self.add_to_session(name=client.session_name, client=client)
        client.bind(property_changed=self.on_client_obj_property_changed)
        #if client.session_name is not None:
        #    self.discovered_sessions.add(client.session_name)
        self.Manager.update_wildcards()
        if self.check_master_attempts is None:
            self.check_for_master(client=client.name)
        propkeys = client.Properties.keys()
        self.LOG.info('add_client:', dict(zip(propkeys, [client.Properties[key].value for key in propkeys])))
        keys = ['name', 'address', 'port']
        s_kwargs = dict(zip(keys, [getattr(client, key) for key in keys]))
        s_kwargs.update({'client':client})
        self.emit('client_added', **s_kwargs)
        
    def remove_client(self, **kwargs):
        name = kwargs.get('name')
        client = self.clients.get(name)
        if client is None:
            return
        #self.remove_client_name(name, update_conf=False)
        #self.remove_client_address(addr, update_conf=False)
        client.unbind(self)
        client.unlink()
        
        del self.clients[name]
        self.Manager.update_wildcards()
        self.LOG.info('remove_client:', name)
        self.emit('client_removed', name=name, client=client)
        if client.session_name is not None:
            self.remove_from_session(name=client.session_name, client=client)
    
    def on_client_obj_property_changed(self, **kwargs):
        prop = kwargs.get('Property')
        old = kwargs.get('old')
        value = kwargs.get('value')
        client = kwargs.get('obj')
        if prop.name == 'isRingMaster' and value is True:
            if self.Manager.ring_master != client.name:
                self.Manager.ring_master = client.name
        elif prop.name == 'isMaster':
            if value is False:
                m = self.determine_next_master()
                if m.name != self.oscMaster:
                    self.select_new_master()
                if self.discovered_sessions.get(client.session_name, {}).get('master') == client:
                    old_session = self.discovered_sessions.copy()
                    self.discovered_sessions[client.session_name]['master'] = None
                    self.discovered_sessions.parent_property.emit(old_session)
            else:
                self.add_to_session(name=client.session_name, client=client)
                
        elif prop.name == 'session_name' and value is not None:
            #self.discovered_sessions.add(value)
            if old is not None:
                self.remove_from_session(name=old, client=client)
            self.add_to_session(name=value, client=client)
#        elif prop.name == 'session_name':
#            if not client.isLocalhost and client.isMaster:
#                pass
#            else:
#                if self.check_master_attempts is not None:
#                    return
#                m = self.determine_next_master()
#                if m.name != self.oscMaster:
#                    self.select_new_master()
#            
#            if client.isSameSession and self.oscMaster == client.name and not client.isLocalhost:
#                self.select_new_master()
#            
#        elif prop.name == 'master_priority':
#            if self.check_master_attempts is not None:
#                return
#            print 'client master pri change: ', client.name, value
#            if client.session_name == self.session_name:
#                m = self.determine_next_master()
#                print 'next master: ', m
#                if m != self.oscMaster:
#                    self.select_new_master()
            
##    def add_client_name(self, name, update_conf=True):
##        s = self.build_curly_wildcard(self.client_names)
##        self.osc_tree._wildcardNodes.discard(s)
##        if name is not None:
##            self.client_names.add(name)
##        if len(self.client_names) > 1 and 'null' in self.client_names:
##            self.client_names.discard('null')
##        s = self.build_curly_wildcard(self.client_names)
##        self.root_node.setName(s)
##        self.osc_tree._wildcardNodes.add(s)
##        if update_conf:
##            self.update_conf(client_names=list(self.client_names))
##        #self.emit('client_added', name=name)
##        
##    def remove_client_name(self, name, update_conf=True):
##        s = self.build_curly_wildcard(self.client_names)
##        self.osc_tree._wildcardNodes.discard(s)
##        self.client_names.discard(name)
##        s = self.build_curly_wildcard(self.client_names)
##        self.root_node.setName(s)
##        self.osc_tree._wildcardNodes.add(s)
##        if update_conf:
##            self.update_conf(client_names=list(self.client_names))
##    
##    def add_client_address(self, address, update_conf=True):
##        if address is not None:
##            self.client_addresses.add(address)
##        if update_conf:
##            self.update_conf(client_addresses=list(self.client_addresses))
##        #self.emit('client_added', name=address)
##        
##    def remove_client_address(self, address, update_conf=True):
##        self.client_addresses.discard(address)
##        if update_conf:
##            self.update_conf(client_addresses=list(self.client_addresses))
        
    def build_zeroconf_data(self):
        d = dict(name=self.local_name, 
                 stype='_osc._udp', 
                 port=self.Manager.ioManager.hostdata['recvport'])
        txt = {'app_name':self.GLOBAL_CONFIG['app_name']}
        #session = self.GLOBAL_CONFIG.get('session_name')
        #if session:
        #    txt['session_name'] = session
        d['text'] = txt
        return d
        
    def build_curly_wildcard(self, l):
        return '{%s}' % (','.join(list(l)))
        
    def _on_master_priority_set(self, **kwargs):
        value = kwargs.get('value')
        #if self.local_client is not None:
        #    self.local_client.master_priority = value
        self.GLOBAL_CONFIG['master_priority'] = value
        self.update_conf(master_priority=value)
        #data = self.build_zeroconf_data()
        #self.comm.ServiceConnector.update_service(**data)
        
    def _on_session_name_set(self, **kwargs):
        value = kwargs.get('value')
        #if self.local_client is not None:
        #    self.local_client.session_name = value
        #    self.local_client.isMaster = False
        self.GLOBAL_CONFIG['session_name'] = value
        #data = self.build_zeroconf_data()
        #self.comm.ServiceConnector.update_service(**data)
        self.select_new_master()
        
    def on_GLOBAL_CONFIG_update(self, **kwargs):
        keys = kwargs.get('keys')
        if not keys:
            keys = [kwargs.get('key')]
        for key in ['master_priority', 'session_name']:
            if key not in keys:
                continue
            value = self.GLOBAL_CONFIG.get(key)
            if value != getattr(self, key):
                setattr(self, key, value)
            
    def on_master_requested_by_osc(self, **kwargs):
        if not self.isRingMaster:
            return
        msg = kwargs.get('message')
        req_session = msg.get_arguments()[0]
        session = self.discovered_sessions.get(req_session, {})
        master = session.get('master')
        if not master:
            return
        self.LOG.info('master_requested_by_osc, session=%s, master=%s' % (req_session, master.name))
        self.setMasterNode.send_message(value=master.name, client=msg.client, timetag=-1)
            
    def on_master_set_by_osc(self, **kwargs):
        msg = kwargs.get('message')
        name = msg.get_arguments()[0]
        self.LOG.info('master_set_by_osc', name)
        self.cancel_check_master_timer()
        self.check_master_attempts = None
        self.set_master(name)
        
    def on_host_discovered(self, **kwargs):
        host = kwargs.get('host')
        #print 'discover:', host.hostdata
        if '.' in host.address:
            c_kwargs = host.hostdata.copy()
            #txt = host.hostdata.get('text', {})
            #m = txt.get('master_priority')
            #if m:
            #    c_kwargs.update({'master_priority':int(m)})
            c_kwargs.update({'discovered':True})
            self.add_client(**c_kwargs)
        #print 'discover:', host.hostdata
        #if socket.gethostname() not in host.hostname:
        #    if host.name not in self.client_names and '.' in host.address:
        #        self.add_client(**host.hostdata)
            
        
    def on_host_removed(self, **kwargs):
        self.LOG.info('remove:', kwargs)
        id = kwargs.get('id')
        self.remove_client(name=id)
        if id == self.oscMaster:
            self.select_new_master()
                
    def check_for_master(self, **kwargs):
        if self.connected and not self.isMaster:
            name = kwargs.get('name')
            if self.check_master_attempts is None:
                self.check_master_attempts = 0
            self.cancel_check_master_timer()
            self.set_master_timeout = threading.Timer(3.0, self.on_check_master_timeout)
            self.set_master_timeout.start()
            #new_kwargs = {}#{'address':'getMaster'}
            #if name:
            #    new_kwargs.update({'client':name})
            element = self.getMasterNode.send_message(value=self.session_name, 
                                                      all_sessions=True, 
                                                      timetag=-1)
            #print 'sent getmaster: ', [str(element)]
            
    def on_check_master_timeout(self):
        self.check_master_attempts += 1
        if self.check_master_attempts == 3:
            self.check_master_attempts = None
            self.set_master()
        else:
            self.check_for_master()
        
    def set_master(self, name=None):
        if self.master_takeover_timer:
            self.master_takeover_timer.cancel()
        if name is None:
            s = self.local_name
        elif name is False:
            s = None
        else:
            s = name
        if s != self.oscMaster:
#            if self.oscMaster is not None:
#                c = self.clients.get(self.oscMaster)
#                if c:
#                    c.isMaster = False
#            c = self.clients.get(s)
#            if c:
#                c.isMaster = True
            self.oscMaster = s
            if self.oscMaster is None:
                return
            if self.isMaster:
                self.local_client.isMaster = True
                self.setMasterNode.send_message(value=self.oscMaster, timetag=-1)
            else:
                self.local_client.isMaster = False
                m = self.determine_next_master()
                if m and m.isLocalhost and name is not False:
                    t = threading.Timer(10.0, self.on_master_takeover_timeout)
                    self.master_takeover_timer = t
                    t.start()
        
        self.LOG.info('master = ', self.oscMaster)
        #self.root_node.oscMaster = self.isMaster
        #self.Manager.stop_clock_send_thread()
        #if self.isMaster:
        #    self.Manager.epoch_offset = datetime.timedelta()
        #    self.Manager.start_clock_send_thread()
        self.determine_ring_master()
        self.emit('new_master', master=self.oscMaster, master_is_local=self.isMaster)
        
    def on_master_takeover_timeout(self):
        m = self.determine_next_master()
        if not m:
            return
        if not self.isMaster and m.isLocalhost:
            self.set_master()
            
    def cancel_check_master_timer(self):
        if self.set_master_timeout and self.set_master_timeout.isAlive:
            self.set_master_timeout.cancel()
            
    def determine_next_master(self):
        d = {}
        for client in self.clients.itervalues():
            if not client.isSameSession:
                continue
            key = client.master_priority
            if key is not None and (client.isSlave or client.isMaster or client.isLocalhost):
                if key in d:
                    if d[key].name < client.name:
                        d[key] = client
                else:
                    d[key] = client
        self.LOG.info('clients by priority: ', d)
        if not len(d):
            return None
        return d[min(d)]
        
    def select_new_master(self):
        self.oscMaster = None
        m = self.determine_next_master()
        if m and m.name == self.local_name:
            self.set_master()
        else:
            self.check_for_master()
            
    def _on_discovered_sessions_set(self, **kwargs):
        #print 'discovered sessions: ', kwargs
        master = self.determine_ring_master()
        if master is False:
            s = 'False'
        else:
            s = ': '.join([master.name, master.address])
        self.LOG.info('ringmaster: ', s)
        
    def _on_ring_master_set(self, **kwargs):
        value = kwargs.get('value')
        self.LOG.info('RINGMASTER: ', value)
        self.local_client.isRingMaster = value == self.local_name
        self.Manager.stop_clock_send_thread()
        if self.isRingMaster:
            self.Manager.epoch_offset = datetime.timedelta()
            self.Manager.start_clock_send_thread()
            
    def _on_oscMaster_set(self, **kwargs):
        self.root_node.oscMaster = self.isMaster
        
class ClockSync(OSCBaseObject):
    _Properties = {'isMaster':dict(default=False), 
                   'offset':dict(default=0.)}
    def __init__(self, **kwargs):
        kwargs.setdefault('osc_address', 'clocksync')
        super(ClockSync, self).__init__(**kwargs)
        self.clients = kwargs.get('clients')
        self.clock_send_thread = None
        self.nodes = {}
        for key in ['sync', 'DelayReq', 'DelayResp']:
            node = self.osc_node.add_child(name=key)
            method = getattr(self, 'on_%s_message_received')
            node.bind(message_received=method)
            self.nodes[key] = node
        self.bind(isMaster=self._on_isMaster_set)
        
    def _on_isMaster_set(self, **kwargs):
        value = kwargs.get('value')
        if value:
            self.start_clock_send_thread()
        else:
            self.stop_clock_send_thread()
            
    def start_clock_send_thread(self):
        self.stop_clock_send_thread()
        self.offset = 0.
        self.clock_send_thread = ClockSender(osc_node=self.nodes['sync'], 
                                             clients=self.clients, 
                                             time_method='timestamp')
        self.clock_send_thread.start()
        
    def stop_clock_send_thread(self, blocking=True):
        if self.clock_send_thread is None:
            return
        self.clock_send_thread.stop(blocking=blocking)
        self.clock_send_thread = None
        
    def on_sync_message_received(self, **kwargs):
        msg = kwargs.get('message')
        times = self.clock_times
        times['master_sync'] = msg.get_arguments()[0]
        times['local_sync'] = msg.timestamp
        #self.delay_req_timestamp = msg.timestamp
        self.nodes['DelayReq'].send_message(client=msg.client, timetag=-1)
        
    def on_DelayReq_message_received(self, **kwargs):
        msg = kwargs.get('message')
        self.nodes['DelayResp'].send_message(value=msg.timestamp, client=msg.client, timetag=-1)
        
    def on_DelayResp_message_received(self, **kwargs):
        msg = kwargs.get('message')
        times = self.clock_times
        times['master_resp'] = msg.get_arguments()[0]
        times['local_resp'] = msg.timestamp
        #netdelay = times['master_resp'] - times['local_resp']
        netdelay = times['local_sync'] - times['local_resp']
        self.offset = times['master_sync'] - times['local_sync'] + (netdelay / 2.)
        
        
class ClockSender(BaseThread):
    def __init__(self, **kwargs):
        kwargs['thread_id'] = 'OSCManager_ClockSender'
        super(ClockSender, self).__init__(**kwargs)
        self._threaded_call_ready.wait_timeout = 10.
        #self.running = threading.Event()
        #self.sending = threading.Event()
        #self.Manager = kwargs.get('Manager')
        self.osc_node = kwargs.get('osc_node')
        self.clients = kwargs.get('clients')
        time_method = kwargs.get('time_method', 'datetime')
        self.time_method = getattr(self, time_method)
        #self.osc_address = kwargs.get('osc_address', 'clocksync')
        #self.interval = kwargs.get('interval', 10.)
    def datetime(self):
        now = datetime.datetime.now()
        return now.strftime('%Y%m%d %H:%M:%S %f')
    def timestamp(self):
        return time.time()
    def _thread_loop_iteration(self):
        if not self.running:
            return
        clients = [c for c in self.clients.values() if c.sendAllUpdates and c.accepts_timetags]# and c.isSameSession]
        #now = datetime.datetime.now()
        #value = now.strftime('%Y%m%d %H:%M:%S %f')
        #value = time.time()
        value = self.time_method()
        self.osc_node.send_message(value=value, 
                                   timetag=-1, 
                                   clients=clients)
    def old_run(self):
        self.running.set()
        self.send_clock()
        while self.running.isSet():
            self.sending.wait(self.interval)
            if self.running.isSet():
                self.send_clock()
            self.sending.clear()
    def old_stop(self):
        self.running.clear()
        self.sending.set()
