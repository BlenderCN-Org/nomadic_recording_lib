import os.path

from kivy.app import App

from Bases import BaseObject, ChildGroup
from bases import widgets

from views.device_control import DeviceControlView
from views.testview import TestView
from views.palettes import PaletteView

views = (DeviceControlView, TestView, PaletteView)
view_classes = dict(zip([cls._view_name for cls in views], views))
    
class MainWindow(BaseObject):
    window_size = {'width':1200, 'height':800}
    def __init__(self, **kwargs):
        super(MainWindow, self).__init__(**kwargs)
        self.MainController = kwargs.get('MainController')
        self.app = KivyApp(MainWindow=self)
        self.app.bind(on_start=self.on_app_start)
        self.app.run()
    def on_fc_selection_made(self, **kwargs):
        self.LOG.info('fc selection made: ', kwargs.get('selection'))
    def on_app_start(self, *args, **kwargs):
        hbox = widgets.HBox(size_hint_y=.05)
        d = {'Open':self.on_btn_open_release, 
             'Save':self.on_btn_save_release, 
             'Connect':self.on_btn_connect_release, 
             'add group':self.on_btn_addgroup_release}
        self.top_btns = {}
        for key, val in d.iteritems():
            btn = widgets.Button(label=key)
            btn.bind(on_release=val)
            hbox.add_widget(btn)
            self.top_btns[key] = btn
        self.app.root.add_widget(hbox)
        
        self.view_hbox = widgets.HBox()
        self.view_selectors = []
        for i in range(2):
            selector = ViewSelector(MainController=self.MainController)
            self.view_hbox.add_widget(selector.topwidget)
            self.view_selectors.append(selector)
        self.app.root.add_widget(self.view_hbox)
        
        #self.view_container = widgets.Widgets.FloatLayout()
        #self.view_selector = ViewSelector(view_container=self.view_container, MainController=self.MainController)
        #self.app.root.add_widget(self.view_selector.topwidget)
        #self.app.root.add_widget(self.view_container)
        
        self.MainController.comm.bind(state_changed=self.on_comm_state_changed)
        #self.current_view = widgets.Dummy(topwidget=widgets.HBox())
        #self.app.root.add_widget(self.current_view.topwidget)
        #hbox = widgets.HBox()
        #self.testattrib = TestAttribute()
        #sld = widgets.VSlider(attribute=self.testattrib)
        #hbox.add_widget(sld.widget)
        
        #hbox.add_widget(fc)
        #txt = widgets.Entry(src_object=self.testattrib, src_attr='name', src_signal='name', name='Name')
        #hbox.add_widget(txt.topwidget)
        #tex = widgets.ColorTest()
        #hbox.add_widget(tex)
        #xy = widgets.XYPad()
        #hbox.add_widget(xy)
        #col = widgets.ColorPicker()
        #hbox.add_widget(col.topwidget)
        #txt = widgets.Entry(name='blah')
        #txt.set_widget_text('stuff')
        #hbox.add_widget(txt.topwidget)
        
        #self.app.root.add_widget(hbox)
        
        
#        tbl = widgets.Table(cols=4, rows=4, size_hint=(None, None))
#        for i in range(16):
#            btn = widgets.Button(label=str(i+1))
#            tbl.add_widget(btn, index=i)
#        print 'tblsize=', tbl.size
#        scr = widgets.ScrolledWindow(size_hint=(None, None), size=(200, 200))
#        scr.add_widget(tbl)
#        self.app.root.add_widget(scr)

    def on_comm_state_changed(self, **kwargs):
        state = kwargs.get('state')
        d = {True:'down', False:'normal'}
        self.top_btns['Connect'].state = d[state]
        
    def open_filechooser(self, **kwargs):
        path = self.MainController.FileManager.most_recent_dir
        if path is None:
            path = '/'
        kwargs.setdefault('path', path)
        fc = widgets.FileChooser(**kwargs)
        fc.bind(selection_made=self.on_filechooser_selection_made)
        return fc
        
    def on_filechooser_selection_made(self, **kwargs):
        filename = kwargs.get('selection')
        chooser = kwargs.get('chooser')
        if chooser.file_mode == 'open':
            self.MainController.load_file(filename=filename)
        elif chooser.file_mode == 'save':
            self.MainController.save_file(filename=filename, json_preset='pretty')
    
    def on_btn_open_release(self, *args):
        self.open_filechooser(file_mode='open')
        
    def on_btn_save_release(self, *args):
        self.open_filechooser(file_mode='save')
        
    def on_btn_connect_release(self, *args):
        comm = self.MainController.comm
        if comm.connected:
            comm.do_disconnect()
        else:
            comm.do_connect()
            
    def on_btn_devcontrol_release(self, *args):
        self.app.root.remove_widget(self.current_view.topwidget)
        self.current_view = DeviceControlView(MainController=self.MainController)
        self.app.root.add_widget(self.current_view.topwidget)
        
    def on_btn_addgroup_release(self, *args):
        self.MainController.add_group()
        
class ViewSelector(BaseObject):
    def __init__(self, **kwargs):
        super(ViewSelector, self).__init__(**kwargs)
        self.MainController = kwargs.get('MainController')
        self.topwidget = widgets.VBox()
        self.btnbox = widgets.HBox(size_hint_y=.05)
        self.topwidget.add_widget(self.btnbox)
        #self.view_container = kwargs.get('view_container')
        #self.view_container = widgets.Widgets.FloatLayout()
        self.view_container = widgets.VBox()
        self.topwidget.add_widget(self.view_container)
        self._current_view = None
        self.view_btns = {}
        for key in view_classes.iterkeys():
            btn = widgets.ToggleBtn(label=key)
            btn.widget.view_key = key
            self.btnbox.add_widget(btn.widget)
            btn.widget.bind(on_release=self.on_view_btn_release)
            self.view_btns[key] = btn
    @property
    def current_view_name(self):
        if self.current_view is None:
            return ''
        return self.current_view._view_name
    @property
    def current_view(self):
        return self._current_view
    @current_view.setter
    def current_view(self, value):
        if self.current_view is not None:
            old = self.current_view._view_name
            self.current_view.unlink()
            self.view_container.remove_widget(self.current_view.topwidget)
            self._current_view = None
        else:
            old = None
        if value != old:
            cls = view_classes[value]
            view = cls(MainController=self.MainController)
            self.view_container.add_widget(view.topwidget)
            self._current_view = view
        for key, btn in self.view_btns.iteritems():
            btn.set_widget_state(self.current_view_name == btn.widget.view_key)
    def on_view_btn_release(self, btn):
        self.current_view = btn.view_key
            
class KivyApp(App):
    def __init__(self, **kwargs):
        self.mainw = kwargs.get('MainWindow')
        self.MainController = self.mainw.MainController
        super(KivyApp, self).__init__(**kwargs)
#    def build_config(self, config):
#        config.setdefaults('graphics', self.mainw.window_size)
#        #config.adddefaultsection('graphics')
#        #for key, val in self.mainw.window_size.iteritems():
#        #    config.set('graphics', key, val)
    def build(self):
        #config = self.config
        #print 'configed size = ', [config.getint('graphics', key) for key in ['width', 'height']]
        box = widgets.VBox()
        #btn = widgets.Button(label='test1')
        #btn.bind(on_press=self.mainw.on_btntest_press)
        #box.add_widget(btn)
        return box
    def on_stop(self):
        self.MainController.on_app_exit()
    
class TestAttribute(BaseObject):
    _Properties = {'name':dict(default=''), 
                   'value':dict(default=0., min=0, max=255)}
    def __init__(self, **kwargs):
        #self._value = 0
        #self._name = 'blah'
        super(TestAttribute, self).__init__(**kwargs)
        self.register_signal('value_changed')
        self.bind(value=self.on_value_set, name=self.on_name_set)
#    @property
#    def value(self):
#        return self._value
#    @value.setter
#    def value(self, value):
#        self._value = value
#        print self, self.value
#        self.emit('value_changed', value=value)
    @property
    def value_min(self):
        return self.Properties['value'].min
    @property
    def value_max(self):
        return self.Properties['value'].max
        
    def on_value_set(self, **kwargs):
        #print kwargs.get('value')
        self.emit('value_changed', value=kwargs.get('value'))
    def on_name_set(self, **kwargs):
        pass
if __name__ == '__main__':
    w = MainWindow()
