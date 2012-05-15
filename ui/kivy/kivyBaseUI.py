from kivy.app import App as _KVApp
from kivy.clock import Clock as _KVClock

from Bases import BaseThread
from .. import BaseUI

from bases import widgets

class Application(BaseUI.Application):
    def __init__(self, **kwargs):
        kwargs['ParentEmissionThread'] = GUIThread(Application=self)
        super(Application, self).__init__(**kwargs)
        self._app_running = False
        self._application = KivyApp(Application=self)
        print 'application: ', self._application
        self._application.bind(on_stop=self.on_mainwindow_close)
    def _build_mainwindow(self, **kwargs):
        print 'buildmainwindow: ', kwargs
        mw = super(Application, self)._build_mainwindow(**kwargs)
        print 'mainwindow built: ', mw
        return mw
    def start_GUI_loop(self, *args):
        #self._app_running = True
        print 'starting app'
        self._application.run()
    def stop_GUI_loop(self):
        running = self._app_running
        self._app_running = False
        if running:
            self._application.stop()
    def emit(self, *args, **kwargs):
        #print 'application emit: ', args, kwargs
        #if args[0] == 'start':
        #    return
        super(Application, self).emit(*args, **kwargs)
    
class KivyApp(_KVApp):
    def __init__(self, **kwargs):
        super(KivyApp, self).__init__(**kwargs)
        self.Application = kwargs.get('Application')
        self._app_name = self.Application.name
        self.title = self.Application.name
        self.Application.bind(name=self.on_Application_name_set)
        
    def build(self):
        print 'KivyApp build'
        return widgets.VBox()
    def on_start(self):
        print 'KivyApp on_start'
        super(KivyApp, self).on_start()
        mw = getattr(self.Application, 'mainwindow', None)
        print 'KivyApp on_start post-super: mw=%s' % (mw)
        if mw is None:
            return
        mw.init_build(self)
        self.Application._app_running = True
    def on_Application_name_set(self, **kwargs):
        name = kwargs.get('value')
        self.title = name
        self._app_name = name

class GUIThread(BaseThread):
    def __init__(self, **kwargs):
        kwargs['thread_id'] = 'GUIThread'
        kwargs['AllowedEmissionThreads'] = ['MainThread']
        self.Application = kwargs.get('Application')
        super(GUIThread, self).__init__(**kwargs)
        self._threaded_call_ready.wait_timeout = None
    def insert_threaded_call(self, call, *args, **kwargs):
        if not self.Application._app_running:
            call(*args, **kwargs)
            return
        print 'guithread insert call: ', call
        super(GUIThread, self).insert_threaded_call(call, *args, **kwargs)
    def _really_do_call(self, p):
        if not self.Application._app_running:
            p()
            return
        print 'guithread insert to kvclock: ', p
        _KVClock.schedule_once(p, -1)
    
class BaseWindow(BaseUI.BaseWindow):
    def init_build(self, app):
        self.app = app
    #def _on_own_property_changed(self, **kwargs):
    #    prop = kwargs.get('Property')
    #    value = kwargs.get('value')
        
