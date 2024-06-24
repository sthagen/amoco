# -*- coding: utf-8 -*-

# This code is part of Amoco
# Copyright (C) 2016-2020 Axel Tillequin (bdcht3@gmail.com)
# published under GPLv2 license

"""
.. _emu:

emu.py
======
The emu module of amoco implements the emulator class :class:`emul`.

"""

from collections import deque

from amoco.config import conf
from amoco.arch.core import DecodeError
from amoco.system.memory import MemoryMapError
from amoco.sa.lsweep import lsweep
from amoco.ui.views import emulView
from amoco.logger import Log

logger = Log(__name__)
logger.debug("loading emu")


class EmulError(Exception):
    pass


class emul_hist(deque):
    def __init__(self, *args, **kargs):
        self.callstack = None
        self.helper = lambda s, i: s
        if "helper" in kargs:
            self.helper = kargs.pop("helper")
        super().__init__(*args, **kargs)

    def append(self, i):
        self.callstack = self.helper(self.callstack, i)
        super().append(i)


class emul(object):
    def __init__(self, task):
        self.task = task
        self.cpu = task.cpu
        # get reference to pc register & size:
        self.pc = task.cpu.getPC()
        self.psz = self.pc.size
        # storage for breakpoints/watchpoints/...
        self.hooks = []
        self.watch = {}
        self.handlers = {}
        # future OS abi support (wip)
        if task.OS is not None:
            self.abi = task.OS.abi
        else:
            self.abi = None
        self.sa = lsweep(task)
        if hasattr(self.task, "helper_callstack"):
            self.hist = emul_hist(
                maxlen=conf.Emu.hist, helper=self.task.helper_callstack
            )
        else:
            self.hist = emul_hist(maxlen=conf.Emu.hist)
        self.callstack = None
        self.view = emulView(self)
        self.handlers[EmulError] = self.stop
        self.handlers[DecodeError] = self.stop
        self.handlers[MemoryMapError] = self.stop

    def stepi(self, trace=False):
        # get PC value in state:
        vaddr = self.task.state(self.pc)
        # It's much better to use the cpu.getPC(state) function for this
        # since the actual target address can be any expression obtained
        # from the current PC register value (including bit masking or
        # fetching data from a code segment (aka x86 cs), etc.
        raddr = self.task.cpu.getPC(self.task.state)
        if raddr._is_top:
            logger.warning("%s has reached top value" % self.pc)
            return None
        if raddr._is_vec:
            logger.warning("%s has too many values, choose one manually" % self.pc)
            return None
        if raddr._is_ext:
            raddr.stub(self.task.state)
            vaddr = self.task.state(self.pc)
            raddr = self.task.cpu.getPC(self.task.state)
        # get instruction @ PC raddr (labeled with vaddr):
        try:
            i = self.task.read_instruction(raddr, label=vaddr)
        except DecodeError:
            logger.warning("decode error at address %s" % vaddr)
            i = None
        if i is not None:
            if trace:
                ops_v = [(self.task.state(o), o) for o in i.operands]
                i.misc["trace"] = ops_v
            if conf.Emu.safe:
                self.task.state.safe_update(i)
            else:
                self.task.state.update(i)
            self.hist.append(i)
            if i.misc.get("delayed", False):
                vaddr += i.length
                islot = self.task.read_instruction(raddr + i.length, label=vaddr)
                if trace:
                    ops_v = [(self.task.state(o), o) for o in islot.operands]
                    islot.misc["trace"] = ops_v
                if conf.Emu.safe:
                    self.task.state.safe_update(islot)
                else:
                    self.task.state.update(islot)
                self.hist.append(islot)
        return i

    def iterate(self, trace=False):
        lasti = None
        while True:
            status, reason = self.checkstate(lasti)
            if status:
                logger.info("stop iteration due to %s" % reason.__doc__)
                if reason.__doc__.startswith("watchpoint"):
                    for x in reason.__defaults__:
                        newx = self.task.state(x)
                        logger.info("new watched value for %s is %s" % (x, newx))
                        self.watch[x] = newx
                break
            try:
                vaddr = self.task.state(self.pc)
                raddr = self.task.cpu.getPC(self.task.state)
                if raddr._is_top:
                    print("can't continue: pc=%s" % (vaddr))
                    raise EmulError()
                if raddr._is_vec:
                    print("too many branches: %s" % (vaddr))
                    raise EmulError()
                lasti = i = self.task.read_instruction(raddr, label=vaddr)
                if trace:
                    ops_v = [(self.task.state(o), o) for o in i.operands]
                    i.misc["trace"] = ops_v
                self.task.state.update(i)
                self.hist.append(i)
                if trace:
                    yield lasti, ops_v
                else:
                    yield lasti
            except Exception as e:
                lasti = None
                # we break only if the handler returns False:
                if not self.exception_handler(e):
                    break
            except KeyboardInterrupt:
                break

    def exception_handler(self, e):
        te = type(e)
        logger.verbose("exception %s received" % te)
        if te in self.handlers:
            return self.handlers[te](self, e)
        raise (e)

    def checkstate(self, prev=None):
        """returns True iff the current state matches a condition that stops
        iterations of instructions. Breakpoints typically return True.
        """
        res = False
        who = None
        if prev is not None:
            for f in self.hooks:
                res |= f(self, prev)
                if res:
                    who = f
                    break
        return res, who

    def breakpoint(self, x=None):
        """add breakpoint hook associated with the provided expression.

        Argument:
        x (int/cst/exp): If x is an int or cst, the break condition
            is assumed to be bool(state(pc==x)).
            Otherwise, the condition is simply bool(state(x)).

        Note: all expressions are evaluated in the state. Thus it
              excludes expressions related to instruction bytes,
              mnemonic or operands. See ibreakpoint method.
        """
        if x is None:
            x = ""
            for index, f in enumerate(self.hooks):
                if f.__doc__.startswith("break"):
                    x += "[% 2d] %s\n" % (index, f.__doc__)
            return x
        if isinstance(x, int):
            x = self.task.cpu.cst(x, self.pc.size)
        if x._is_cst:
            x = self.pc == x
        f = lambda e, prev, expr=x: bool(e.task.state(expr))
        f.__doc__ = "breakpoint: %s" % x
        self.hooks.append(f)
        return x

    def watchpoint(self, x=None):
        """add watchpoint hook associated with provided expression.

        Argument:
        x (int/cst/exp): If x is an int or cst, break occurs
            when state(mem(x,8)) changes (symbolic) value.
            Otherwise, break occurs when state(x) changes value.
            Initial value is taken from the watchpoint creation state.
        """
        if x is None:
            x = ""
            for index, f in enumerate(self.hooks):
                if f.__doc__.startswith("watch"):
                    x += "[% 2d] %s\n" % (index, f.__doc__)
            return x
        if isinstance(x, int):
            x = self.task.cpu.cst(x, self.pc.size)
        if x._is_cst:
            x = self.task.cpu.mem(x, 8)
        self.watch[x] = self.task.state(x)
        f = lambda e, prev, expr=x: bool(e.task.state(expr) != e.watch[expr])
        f.__doc__ = "watchpoint: %s" % x
        self.hooks.append(f)
        return x

    def ibreakpoint(self, mnemonic="", dst=None, src=None):
        """add breakpoint hook related to specific instruction form.
        Currently supports breaking on mnemonic and/or destination
        operand or any source operand.

        Arguments:
        mnemonic (str): breaks *after* next instruction matching mnemonic.
        dst (int/cst/exp): break on matching destination operand.
        src (int/cst/exp): break on matching any source operand.

        Note:
        like for breakpoint/watchpoint, if dst/src is an int or
        a cst expression, the input value is assumed to represent the
        address of dst/src (ie. ptr(dst) or ptr(src).)
        """

        def cast(x):
            if x is not None:
                if isinstance(x, int):
                    x = self.task.cpu.cst(x, self.pc.size)
                if x._is_cst:
                    x = self.task.cpu.ptr(x)
            return x

        dst = cast(dst)
        src = cast(src)

        def check(e, prev, mnemo=mnemonic, xdest=dst, xsrc=src):
            if mnemo:
                cond = prev.mnemonic.lower() == mnemo
                if not cond:
                    return False
            else:
                cond = False
            if xdest is not None or xsrc is not None:
                m = e.task.state.__class__()
                m = prev(m)
                if xdest is not None:
                    cond = any((bool(e.task.state(x == xdest)) for x, _ in m))
                    if not cond:
                        return False
                if xsrc is not None:
                    cond = any((bool(e.task.state(x == xsrc)) for _, x in m))
                    if not cond:
                        return False
            return cond

        doc = "breakpoint: "
        if mnemonic:
            doc += "%s " % mnemonic
        if dst:
            doc += "dst: %s " % str(dst)
        if src:
            doc += "src: %s" % str(dst)
        check.__doc__ = doc
        self.hooks.append(check)
        return doc

    def tracepoint(self, x=None, act=None, file=None):
        """add tracepoint hook associated with provided expression.

        Argument:
        x (int/cst/exp): If x is an int or cst, the provided action
            is triggered when bool(state(pc==x)) is True (ie the value
            is assumed to represent an instruction's address.
            Otherwise, action is triggered simply when bool(state(x))
            is True.
        act (list[(expr,expr)]): The action consist in a list of
           (lx,rx) directives to print/modify locations of the
           current state (print if rx is None). Directives are applied
           in given order. If rx is not None, the action is
           state[lx] = state(rx).
           If act is None, a copy of the state is printed to file.
        file: The file in which to append printed directives.
           If act is None, and no file is provided, it is created with
           tempfile.mkstemp(prefix='amoco-trace-%s'%x,suffix='.dump')
        """
        if x is None:
            x = ""
            for index, f in enumerate(self.hooks):
                if f.__doc__.startswith("trace"):
                    x += "[% 2d] %s\n" % (index, f.__doc__)
            return x
        if isinstance(x, int):
            x = self.task.cpu.cst(x, self.pc.size)
        if x._is_cst:
            x = self.pc == x
        if act is None and (not file):
            import tempfile

            file = tempfile.mkstemp(prefix="amoco-trace-%s.dump" % x, suffix=".dump")

        def tp(e, prev, expr=x, act=act, f=file):
            "tracepoint:"
            if bool(e.task.state(expr)):
                if act is None:
                    print(e.task.state, file=f)
                else:
                    for lx, rx in act:
                        if rx is None:
                            print("%s: %s" % (lx, e.task.state(lx)), file=f)
                        else:
                            try:
                                e.task.setx(lx, rx)
                                msg = "tracepoint: %s" % expr
                                logger.verbose("%s: %s <- %s" % (msg, lx, rx))
                            except Exception:
                                logger.error("tracepoint error")
            return False

        tp.__doc__ = "tracepoint: %s" % x
        self.hooks.append(tp)
        return x

    def stop(self, *args, **kargs):
        return False

    def from_db(self, data):
        logger.verbose("loading data from %s" % data)
        self.task.cpu.internals.update(data.cpuinternals)
        self.task.state = data.state
        for hdoc, hdefs in data.hooks.items():
            logger.info("added %s" % hdoc)
            if hdoc.startswith("watchpoint"):
                for x in hdefs:
                    self.watchpoint(x)
            elif hdoc.startswith("tracepoint"):
                self.tracepoint(*hdefs)
            else:
                self.breakpoint(*hdefs)
        self.watch.update(data.watch)
