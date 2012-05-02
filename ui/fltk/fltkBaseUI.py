from Bases import BaseObject, BaseThread
from .. import BaseUI

from bases.ui_modules import fltk

class Application(BaseUI.Application):
    def __init__(self, **kwargs):
        kwargs['ParentEmissionThread'] = GUIThread
        super(Application, self).__init__(**kwargs)
        
class GUIThread(BaseThread):
    def __init__(self, **kwargs):
        kwargs['thread_id'] = 'GUIThread'
        super(GUIThread, self).__init__(**kwargs)
    def _thread_loop_iteration(self):
        r = fltk.check()
        
