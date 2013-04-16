class AcquireBase(object):
    name = None
    
class AcquirePIP(AcquireBase):
    name = 'pip'
    
class AcquireEasyInstall(AcquireBase):
    name = 'easy_install'
    
class AcquireApt(AcquireBase):
    name = 'apt'
