from amoco.cas.expressions import top, cst
from types import MethodType
from amoco.logger import Log

logger = Log(__name__)
logger.debug("loading module")


class DefineIO:
    def __init__(self, port, name=None):
        self.io = IO(port, name)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        IO.ports[self.io.port] = self.io

    def In(self, func):
        self.io.In = MethodType(func, self.io)
        return func

    def Out(self, func):
        self.io.Out = MethodType(func, self.io)
        return func


class IO:
    ports = {}

    @classmethod
    def get_port(cls, port):
        if isinstance(port, cst):
            port = port.v
        return cls.ports.get(port, cls(port))

    def __init__(self, port, name=None):
        self.port = port
        self.name = name or "IO#0x%x" % port

    def In(self, env, dl):
        logger.warning("undefined %s IN" % str(self))
        return top(dl * 8)

    def Out(self, env, src):
        logger.warning("undefined %s OUT (%s)" % (str(self), src))

    def __str__(self):
        return self.name
