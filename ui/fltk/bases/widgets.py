from ui_modules import fltk

from Bases import BaseObject
from Bases.SignalDispatcher import dispatcher

gui_thread = BaseObject().GLOBAL_CONFIG.get('GUIThread')

class Window(fltk.Fl_Window, dispatcher):
    def __init__(self, *args):
        self.ParentEmissionThread = gui_thread
        self.register_signal('resize')
        super(Window, self).__init__(*args)
        
    def resize(self, *args):
        print 'window resize: ', args
        super(Window, self).resize(*args)
        self.emit('resize', position=args[:2], size=args[2:])
