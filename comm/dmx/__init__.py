from NetlinxDMX import NetlinxDMX
try:
    from usb_pro import USBProIO
except ImportError:
    USBProIO = None
from artnet.manager import ArtnetManager

class olaLoader(type):
    ui_name = 'OLA (Open Lighting Architecture)'
    def __new__(self, *args, **kwargs):
        from dmx.OSCtoOLA import OSCtoOLAHost
        return OSCtoOLAHost(*args, **kwargs)

IO_LOADER = {'NetlinxDMX':NetlinxDMX,
             'ola_IO':olaLoader,
             'Artnet':ArtnetManager}
if USBProIO is not None:
    IO_LOADER['USBPro'] = USBProIO
