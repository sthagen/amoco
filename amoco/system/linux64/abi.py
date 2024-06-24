import ctypes
import ctypes.util

from amoco.logger import Log

logger = Log(__name__)
logger.debug("loading module")


class cdecl(object):
    pass


class demangler:
    def __init__(self):
        libc_n = ctypes.util.find_library("c")
        libcxx_n = ctypes.util.find_library("stdc++") or ctypes.util.find_library("c++")
        libc = ctypes.CDLL(libc_n)
        libcxx = ctypes.CDLL(libcxx_n)
        self._free = libc.free
        self._free.argtypes = [ctypes.c_void_p]
        self._cxa_demangle = getattr(libcxx, "__cxa_demangle")
        self._cxa_demangle.restype = type("charptr", (ctypes.c_char_p,), {})

    def demangle(self, name):
        if not name.startswith("_Z"):
            return name
        mn = ctypes.c_char_p(name.encode())
        status = ctypes.c_int()
        retval = self._cxa_demangle(mn, None, None, ctypes.pointer(status))
        try:
            n = retval.value
        finally:
            self._free(retval)
        if status.value == 0:
            return n.decode()
        else:
            logger.warning("failed to demangle symbol '%s'" % name)
            return name


demangle = demangler().demangle
