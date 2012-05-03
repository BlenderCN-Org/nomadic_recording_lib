from Bases import BaseObject, BaseThread
from .. import BaseUI

from bases.ui_modules import fltk
from bases import widgets

class Application(BaseUI.Application):
    def __init__(self, **kwargs):
        self.GUIThread = GUIThread()
        self.GUIThread.start()
        kwargs['ParentEmissionThread'] = self.GUIThread
        super(Application, self).__init__(**kwargs)
        self.GUIThread.bind(_stopped=self.on_GUIThread_stopped)
    def start_GUI_loop(self, join=False):
        self.GUIThread.gui_running = True
        if not join:
            return
        self.GUIThread.join()
    def stop_GUI_loop(self):
        self.GUIThread.gui_running = False
    def on_GUIThread_stopped(self, **kwargs):
        if kwargs.get('value') is True:
            self.emit('exit')
        
        
class GUIThread(BaseThread):
    def __init__(self, **kwargs):
        kwargs['thread_id'] = 'GUIThread'
        self.gui_running = False
        super(GUIThread, self).__init__(**kwargs)
    def _thread_loop_iteration(self):
        if not self.gui_running:
            return
        r = fltk.Fl_check()
        if r == 0:
            self._running = False
        
class BaseWindow(BaseUI.BaseWindow):
    def __init__(self, **kwargs):
        self._updating_dimensions = False
        super(BaseWindow, self).__init__(**kwargs)
    def _build_window(self, **kwargs):
        args = [40, 40]
        args.extend(self.size[:])
        args.append(self.title)
        w = widgets.Window(*args)
        w.end()
        w.connect('resize', self._on_window_resize)
        return w
        
    def _update_window_dimensions(self):
        self._updating_dimensions = True
        d = {'position':['x', 'y'], 'size':['w', 'h']}
        for attr, keys in d.iteritems():
            value = [getattr(self.window, key)() for key in keys]
            if value == getattr(self, attr):
                continue
            setattr(self, attr, value)
        self._updating_dimensions = False
        
    def _on_own_property_changed(self, **kwargs):
        prop = kwargs.get('Property')
        value = kwargs.get('value')
        if value is None:
            return
        if prop.name == 'size':
            if self._updating_dimensions:
                return
            self.window.size(*value)
        elif prop.name == 'title':
            self.window.label(value)
        elif prop.name == 'fullscreen':
            if value:
                #self._update_window_dimensions()
                self.window.fullscreen()
            else:
                args = self.position[:] + self.size[:]
                self.window.fullscreen_off(*args)
                
    def _on_window_resize(self, **kwargs):
        self._updating_dimensions = True
        for key in ['position', 'size']:
            value = list(kwargs.get(key))
            setattr(self, key, value)
            print key, value, getattr(self, key)
        self._updating_dimensions = False
