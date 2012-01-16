#  This file is part of OpenLightingDesigner.
# 
#  OpenLightingDesigner is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  OpenLightingDesigner is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with OpenLightingDesigner.  If not, see <http://www.gnu.org/licenses/>.
#
# CommDispatcher.py
# Copyright (c) 2010 - 2011 Matthew Reid

import os.path
import pkgutil

import BaseIO
from interprocess.ServiceConnector import ServiceConnector

from . import IO_CLASSES


class CommDispatcherBase(BaseIO.BaseIO):
    def __init__(self, **kwargs):
        super(CommDispatcherBase, self).__init__(**kwargs)
        self.IO_MODULES = {}
        self.ServiceConnector = ServiceConnector()
    
    @property
    def SystemData(self):
        return self.GLOBAL_CONFIG.get('SystemData')
    
    @property
    def IO_CLASSES(self):
        return IO_CLASSES
        
    def do_connect(self, **kwargs):
        self.ServiceConnector.publish()
        self.connected = True
        
    def do_disconnect(self, **kwargs):
        self.ServiceConnector.unpublish()
        self.connected = False
        
    def shutdown(self):
        self.ServiceConnector.unpublish(blocking=True)
        self.connected = False
    
    def build_io_module(self, name, **kwargs):
        cls = self.IO_CLASSES.get(name)
        if not cls:
            return
        kwargs.setdefault('comm', self)
        obj = cls(**kwargs)
        self.IO_MODULES[name] = obj
        return obj

