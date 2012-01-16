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

import BaseIO
from interprocess.SystemData import SystemData
from interprocess.ServiceConnector import ServiceConnector

class CommDispatcherBase(BaseIO.BaseIO):
    def __init__(self, **kwargs):
        super(CommDispatcherBase, self).__init__(**kwargs)
        self.SystemData = SystemData()
        self.ServiceConnector = ServiceConnector(SystemData=self.SystemData)
        
    def do_connect(self, **kwargs):
        self.ServiceConnector.publish()
        self.connected = True
        
    def do_disconnect(self, **kwargs):
        self.ServiceConnector.unpublish()
        self.connected = False
        
    def shutdown(self):
        self.ServiceConnector.unpublish(blocking=True)
        self.connected = False
    
