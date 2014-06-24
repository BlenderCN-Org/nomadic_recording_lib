import threading


class CLICommandError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)
class CLICommandNoResponseError(CLICommandError):
    pass
class CLICommandInvalidResponseError(CLICommandError):
    pass
    
class CommandContext(object):
    def __init__(self, cmd_obj):
        self.command_obj = cmd_obj
        self.event = threading.Event()
        self.complete = False
    @property
    def active(self):
        return self.event.is_set()
    def __enter__(self):
        self.event.set()
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.complete = True
        self.event.clear()

class BaseCommand(object):
    _command_classes = {}
    def __init__(self, **kwargs):
        '''
            command: (str) command to transmit
            prompt: (str) required for the root command (model string ending with ">")
        '''
        command = kwargs.get('command', getattr(self, 'command', None))
        self.command = command
        exit_command = kwargs.get('exit_command', getattr(self, 'exit_command', None))
        self.exit_command = exit_command
        self._prompt = kwargs.get('prompt')
        self.parent = kwargs.get('parent')
        self.context = CommandContext(self)
        self._message_io = kwargs.get('message_io')
        self.is_root = self.parent is None
        self.children = []
        for ckwargs in kwargs.get('children', []):
            self.add_child(**ckwargs)
    @classmethod
    def build_cmd(cls, **kwargs):
        _cls = kwargs.get('cls')
        if _cls is not None:
            if isinstance(_cls, basestring):
                _cls = BaseCommand._command_classes.get(_cls)
            cls = _cls
        return cls(**kwargs)
    def add_child(self, **kwargs):
        kwargs['parent'] = self
        child = self.build_cmd(**kwargs)
        self.children.append(child)
        return child
    @property
    def root(self):
        if self.is_root:
            return self
        return self.parent.root
    @property
    def message_io(self):
        m_io = self._message_io
        if m_io is not None:
            return m_io
        return self.parent.message_io
    @property
    def prompt(self):
        prompt = self._prompt
        if prompt is not None:
            return prompt
        prompt = self._prompt = self.get_prompt()
        return prompt
    def get_prompt(self):
        return self.parent.prompt
    def __call__(self):
        with self.context:
            msg = self.message_io.build_tx(content=self.command + '\n', read_until=self.prompt)
            valid = self.validate_response(msg)
            for child in self.children:
                child()
            if self.exit_command is not None:
                if self.parent is not None:
                    read_until = self.parent.prompt
                else:
                    read_until = None
                exit_msg = self.message_io.build_tx(content=self.exit_command + '\n', read_until=read_until)
                if read_until is not None:
                    self.parent.validate_response(exit_msg)
            else:
                exit_msg = None
            self.response_message = msg
            self.exit_message = exit_msg
    def validate_response(self, msg):
        if msg is None:
            raise CLICommandNoResponseError(self)
        last_line = msg.content.splitlines()[-1]
        if self.prompt not in last_line:
            raise CLICommandInvalidResponseError(self)
        return True
        
class LoginCommand(BaseCommand):
    def get_prompt(self):
        return 'login as: '
class PasswordCommand(BaseCommand):
    exit_command = 'logout'
    def get_prompt(self):
        return 'password: '
class MenuCommand(BaseCommand):
    exit_command = 'exit'
    def __init__(self, **kwargs):
        super(MenuCommand, self).__init__(**kwargs)
    def get_prompt(self):
        prompt = self.parent.prompt.rstrip('>')
        prompt = '/'.join([prompt, self.command])
        return prompt + '>'
        
