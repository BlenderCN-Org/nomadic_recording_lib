import threading
from bases.ui_modules import gtk, gio, gdk, glib

from Bases import BaseObject, BaseThread
from .. import BaseUI

#from bases.widgets import get_widget_classes, get_container_classes


class Application(BaseObject):
    def __init__(self, **kwargs):
        kwargs['ParentEmissionThread'] = gtksimple.gCBThread
        super(Application, self).__init__(**kwargs)
        self.register_signal('start', 'exit')
        self.name = kwargs.get('name', self.GLOBAL_CONFIG.get('app_name'))
        self.app_id = kwargs.get('app_id', self.GLOBAL_CONFIG.get('app_id'))
        self.mainwindow_kwargs = kwargs.get('mainwindow_kwargs', {})
        self.GLOBAL_CONFIG['GUIApplication'] = self
        if self.GLOBAL_CONFIG['gtk_version'] >= 3:
            self.app_flags = gio.ApplicationFlags(0)
            self._application = gtk.Application.new(self.app_id, self.app_flags)
        else:
            self._application = None
    
    def run(self):
        mwkwargs = self.mainwindow_kwargs.copy()
        mwkwargs['Application'] = self
        self.mainwindow = MainWindow(**mwkwargs)
        self.mainwindow.window.connect('destroy', self.on_mainwindow_destroy)
        self.emit('start')
        #self.GLoopThread = GUIThread()
        #self.GLoopThread.start()
        gdk.threads_enter()
        gtk.main()
        gdk.threads_leave()
        
    def on_mainwindow_destroy(self, *args, **kwargs):
        self.stop_ParentEmissionThread()
        gtk.main_quit()
        #self.GLoopThread.stop(blocking=True)
        self.emit('exit')
        
from bases import widgets, gtksimple

class GUIThread(BaseThread):
    def __init__(self, **kwargs):
        kwargs['thread_id'] = 'GUIThread'
        super(GUIThread, self).__init__(**kwargs)
        self._threaded_call_ready.wait_timeout = None
    def insert_threaded_call(self, call, *args, **kwargs):
        if threading.currentThread().name in ['MainThread', self._thread_id, gtksimple.gCBThread._thread_id]:
            call(*args, **kwargs)
        else:
            gtksimple.gCBThread.add_callback(call, *args, **kwargs)
    def stop(self, **kwargs):
        gtksimple.gCBThread.stop(**kwargs)
        super(GUIThread, self).stop(**kwargs)
        
widget_classes = widgets.get_widget_classes()
container_classes = widgets.get_container_classes()

class BaseWindow(BaseObject):
    def __init__(self, **kwargs):
        kwargs['ParentEmissionThread'] = kwargs['Application'].ParentEmissionThread
        super(BaseWindow, self).__init__(**kwargs)
        self.window = gtk.Window()
        if hasattr(self, 'topwidget_name'):
            kwargs.setdefault('topwidget_name', self.topwidget_name)
        title = kwargs.get('topwidget_name', '')
        self.window.set_title(title)
        self._Application = None
        self.Application = kwargs.get('Application')
        if hasattr(self, 'window_size'):
            kwargs.setdefault('window_size', self.window_size)
        size = kwargs.get('window_size', (300, 300))
        self.window.set_property('default_width', size[0])
        self.window.set_property('default_height', size[1])
        self.child_windows = {}
        self.widgets = {}
        
    @property
    def Application(self):
        return self._Application
    @Application.setter
    def Application(self, value):
        if self.Application is not None:
            self.Application._application.remove_window(self.window)
        self._Application = value
        if self.Application is not None:
            if self.Application._application is not None:
                self.Application._application.add_window(self.window)
            self.window.set_title(self.Application.name)
        
    def make_child_window(self, cls, name, **kwargs):
        w = cls(**kwargs)
        #w.window.set_parent_window(self.window)
        #w.window.set_destroy_with_parent(True)
        w.window.connect('destroy', self.on_childwindow_destroyed, name)
        self.child_windows.update({name:w})
        
    def on_childwindow_destroyed(self, obj, name):
        if name in self.child_windows:
            del self.child_windows[name]
            
    def make_child_widget(self, cls, widget_name, **kwargs):
        widget = cls(**kwargs)
        self.widgets.update({widget_name:widget})
        return widget
        
    def remove_child_widget(self, widget_name):
        widget = self.widgets.get(widget_name)
        if widget is not None:
            widget.get_parent().remove(widget)
            del self.widgets[widget_name]
            return True
        return False

class BaseContainer(BaseUI.BaseContainer):
    container_classes = widgets.get_container_classes()
    widget_classes = widgets.get_widget_classes()
    # TODO: make this use the container class in widgets module
    def add_child(self, widget, **kwargs):
        if isinstance(self.topcontainer, gtk.Table):
            expand = kwargs.get('expand')
            if expand is not None:
                del kwargs['expand']
                if expand:
                    kwargs.setdefault('xoptions', gtk.EXPAND | gtk.FILL)
                    kwargs.setdefault('yoptions', gtk.EXPAND | gtk.FILL)
                    #print 'xoptions', kwargs.get('xoptions')
            else:
                kwargs.setdefault('xoptions', gtk.FILL)
                kwargs.setdefault('yoptions', gtk.FILL)
            sizeX = self.topcontainer.get_property('n-columns')
            sizeY = self.topcontainer.get_property('n-rows')
            loc = None
            for x in range(sizeX):
                for y in range(sizeY):
                    if (x, y) not in self._child_widgets_locations:
                        loc = (x, y)
                        break
            if loc is None:
                self.topcontainer.resize(sizeY+1, sizeX)
                loc = (sizeX, sizeY+1)
            self.topcontainer.attach(widget, loc[0], loc[0]+1, loc[1], loc[1]+1, **kwargs)
            self._child_widgets_locations.update({loc:widget})
        else:
            kwargs.setdefault('expand', False)
            
            self.topcontainer.pack_start(widget, **kwargs)

class ControlContainer(BaseUI.ControlContainer):
    container_classes = widgets.get_container_classes()
    widget_classes = widgets.get_widget_classes()
    def build_children(self):
        cinfo = self.section.child_container
        size = cinfo.get('size')
        cboxkwargs = {}
        if size is not None:
            cboxkwargs.update({'rows':size[1], 'columns':size[0]})
        #cbox = self.container_classes.get(cinfo.get('cls', 'VBox'))(**cboxkwargs)
        book = self.container_classes.get('Notebook')()
        #print 'name %s,cboxclass %s, kwargs %s' % (self.section.name, cinfo.get('cls'), cboxkwargs)
        #for key, val in self.section.children.iteritems():
        keys = self.section.child_order
        if keys is None:
            keys = self.section.children.keys()
        for key in keys:
            val = self.section.children[key]
            self.children.update({key:{}})
            for cKey, cVal in val.iteritems():
                #topwidget = self.container_classes.get(cVal.container_widget, self.container_classes['VBox'])
                #topwidget = self.container_classes['Frame']
                #topwidget = self.container_classes.get(cVal.container_widget, self.container_classes['VBox'])
                #twkwargs = {}
                #if cVal.container_size is not None:
                #    twkwargs.update({'rows':cVal.container_size[0], 'columns':cVal.container_size[1]})
                #if topwidget is None:
                #    topwidget = VBox
                child = ControlContainer(section=cVal, 
                                         container_classes=self.container_classes, 
                                         widget_classes=self.widget_classes)
                #self.add_child(child.topwidget)
                #cbox.pack_end(child.topwidget)
                book.add_page(widget=child.topwidget, label=child._topwidget_name)
                self.children[key].update({cKey:child})
            self.add_child(book)


from mainwindow import MainWindow
