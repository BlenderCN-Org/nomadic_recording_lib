from __future__ import print_function
import logging

from BaseObject import BaseObject
from config import Config

LEVELS = ('debug', 'info', 'warning', 'error', 'critical')

class Logger(BaseObject, Config):
    _confsection = 'LOGGING'
    _Properties = {'log_mode':dict(default='stdout', entries=['basicConfig', 'stdout']), 
                   'log_filename':dict(type=str), 
                   'log_level':dict(default='info', fformat='_format_log_level'), 
                   'log_format':dict(default='%(asctime)-15s %(levelname)-10s %(message)s')}
    _confkeys = ['log_mode', 'log_filename', 'log_level', 'log_format']
    def __init__(self, **kwargs):
        BaseObject.__init__(self, **kwargs)
        Config.__init__(self, **kwargs)
        appname = self.GLOBAL_CONFIG.get('app_name')
        if appname is not None:
            kwargs.setdefault('log_filename', os.path.expanduser('~/%s.log' % (appname)))
        self._logger = None
        d = self.get_conf()
        for key in self._confkeys:
            val = d.get(key)
            if val is None:
                val = kwargs.get(key)
            if val is None:
                continue
            setattr(self, key, val)
        self.set_logger()
        self.bind(property_changed=self._on_own_property_changed)
    def _format_log_level(self, value):
        if type(value) == str and value.isdigit():
            value = int(value)
        if type(value) == int:
            value = LEVELS[value]
        return value
    def set_logger(self, name=None):
        if name is None:
            name = self.log_mode
        cls = LOGGERS[name]
        keys = ['filename', 'level', 'format']
        lkwargs = dict(zip(keys, [getattr(self, '_'.join(['log', key])) for key in keys]))
        self._logger = cls(**lkwargs)
        for key in ['log', 'debug', 'info', 'warning', 'error', 'critical', 'exception']:
            m = getattr(self._logger, key)
            setattr(self, key, m)
    def _on_own_property_changed(self, **kwargs):
        prop = kwargs.get('Property')
        value = kwargs.get('value')
        if prop.name == 'log_level':
            self._logger.level = value
    
def format_msg(*args):
    if len(args) <= 1:
        return str(args[0])
    return ', '.join([str(arg) for arg in args])
    
class StdoutLogger(object):
    def __init__(self, **kwargs):
        pass
    def log(self, level, *args, **kwargs):
        msg = format_msg(*args)
        print (': '.join([level, msg]))
    def debug(self, *args, **kwargs):
        self.log('debug', *args, **kwargs)
    def info(self, *args, **kwargs):
        self.log('info', *args, **kwargs)
    def warning(self, *args, **kwargs):
        self.log('warning', *args, **kwargs)
    def error(self, *args, **kwargs):
        self.log('error', *args, **kwargs)
    def critical(self, *args, **kwargs):
        self.log('critical', *args, **kwargs)
    def exception(self, *args, **kwargs):
        self.log('exception', *args, **kwargs)
        
class BasicConfigLogger(object):
    def __init__(self, **kwargs):
        logging.basicConfig(**kwargs)
    def log(self, level, *args, **kwargs):
        msg = format_msg(*args)
        logging.log(level, msg, **kwargs)
    def debug(self, *args, **kwargs):
        msg = format_msg(*args)
        logging.debug(msg, **kwargs)
    def info(self, *args, **kwargs):
        msg = format_msg(*args)
        logging.info(msg, **kwargs)
    def warning(self, *args, **kwargs):
        msg = format_msg(*args)
        logging.warning(msg, **kwargs)
    def error(self, *args, **kwargs):
        msg = format_msg(*args)
        logging.error(msg, **kwargs)
    def critical(self, *args, **kwargs):
        msg = format_msg(*args)
        logging.critical(msg, **kwargs)
    def exception(self, *args, **kwargs):
        msg = format_msg(*args)
        logging.exception(msg, **kwargs)
        
LOGGERS = {'stdout':StdoutLogger, 'basicConfig':BasicConfigLogger}
