# -*- coding: utf-8 -*-

# This code is part of Amoco
# Copyright (C) 2018-2020 Axel Tillequin (bdcht3@gmail.com)
# published under GPLv2 license

"""
srv.py
======

This module defines a set of high-level commands that allow
to use amoco from a dedicated command-line interface.
"""

import ctypes
import re
import multiprocessing as mp
import queue
import time
from rich import progress as rp
from amoco.config import conf
from amoco.ui.cli import cmdcli_builder

from amoco.logger import Log

logger = Log(__name__)
logger.debug("loading module")


STOPPED = 0
IDLE = 1
WAITING = 2
STALLED = 3


class DefineSrvCommand(object):
    """decorator that allows to "register" commands on-the-fly"""

    def __init__(self, serv, name, alias=None):
        self.serv = serv
        self.name = name
        if alias is None:
            alias = []
        self.alias = alias
        if self.name not in serv.cmds:
            serv.cmds[self.name] = None

    def __call__(self, cls):
        logger.verbose("DefineCommand %s:%s" % (self.name, cls))
        cmd = cls()
        self.serv.cmds[self.name] = cmd
        for alias in self.alias:
            self.serv.cmds[alias] = cmd
        return cls


class srv(object):
    cmds = {}

    def __init__(self, scope=None, obj=""):
        if scope is None:
            scope = globals()
        self.scope = scope
        self.obj = obj
        self._srv = None
        self.history = ""
        self.lastcmd = None

    def start(self, daemon=True, timeout=conf.Server.timeout):
        def do_cmd(i, cmdline):
            self.history += "%s\n" % cmdline
            args = cmdline.split()
            cmd = args[0]
            if cmd in self.cmds:
                res = self.cmds[cmd].run(self, args)
                self.lastcmd = cmd
            else:
                logger.debug("command not found: %s" % cmd)
                res = 0
            return res

        def mainloop(ctrl, msgs, outs):
            i = 0
            while True:
                try:
                    cmdline = ctrl.get()
                except queue.Empty:
                    break
                else:
                    if cmdline.endswith("&"):
                        cmdline = cmdline.replace("&", "")
                        p = mp.Process(target=do_cmd, args=(i, cmdline))
                        p.start()
                        p.join(timeout)
                        if p.is_alive():
                            p.terminate()
                        outs.put(p.exitcode)
                    else:
                        res = do_cmd(i, cmdline)
                        outs.put(res)
                    i += 1
            logger.verbose("server stopped (queue is empty.)")
            return i

        self.shar = mp.Array(ctypes.c_ubyte, [0] * conf.Server.wbsz)
        self.ctrl = mp.Queue()
        self.msgs = mp.Queue()
        self.outs = mp.Queue()
        if daemon:
            self._srv = mp.Process(
                target=mainloop, args=(self.ctrl, self.msgs, self.outs)
            )
            self._srv.start()
        else:
            self._do_cmd = do_cmd
        self.interact()
        if self._srv and self._srv.is_alive():
            self._srv.terminate()
            logger.verbose("server process terminated.")
        self._srv = None

    def interact(self):
        if conf.UI.cli == "cmdcli":
            cmdcli_builder(srv=self).cmdloop()


# -----------------------------------------------------------------------------


@DefineSrvCommand(srv, "hello")
class cmd_hello(object):
    "hello: response from server indicating the daemon pid and loaded object."

    @staticmethod
    def run(srv, args):
        s = "server process is running"
        if srv._srv and srv._srv.pid:
            s += " (daemon pid:%d)" % srv._srv.pid
        L = ["%s." % s]
        if srv.obj:
            L.append("%s is loaded" % srv.obj)
        srv.msgs.put("\n".join(L))
        # wait for new command (don't quit client loop):
        return 0


# -----------------------------------------------------------------------------


@DefineSrvCommand(srv, "history", ["h"])
class cmd_history(object):
    "history: show all commands issued so far."

    @staticmethod
    def run(srv, args):
        srv.msgs.put(srv.history)
        # wait for new command (don't quit client loop):
        return 0


# -----------------------------------------------------------------------------


@DefineSrvCommand(srv, "load")
class cmd_load(object):
    "load FILENAME: instanciate server's emul object if none is loaded."

    @staticmethod
    def run(srv, args):
        if len(args) == 2:
            filename = args[1]
            if not srv.obj:
                from amoco.system import load_program
                from amoco.emu import emul

                srv.obj = emul(load_program(filename))
            else:
                srv.msgs.put("already loaded:")
        srv.msgs.put(str(srv.obj))
        # wait for new command (don't quit client loop):
        return 0


# -----------------------------------------------------------------------------


@DefineSrvCommand(srv, "save")
class cmd_save(object):
    "save [name]: save the current server's emul object in database."

    @staticmethod
    def run(srv, args):
        args.pop(0)  # cmd
        if len(args):
            name = args.pop(0)
        else:
            name = None
        from amoco.db import EmuData, session

        cur = EmuData(srv.obj, name=name)
        session.add(cur)
        srv.msgs.put("commit: %s" % repr(cur))
        session.commit()
        # wait for new command (don't quit client loop):
        return 0


# -----------------------------------------------------------------------------


@DefineSrvCommand(srv, "restore")
class cmd_restore(object):
    "restore [name]: restore a server's emul object from database."

    @staticmethod
    def run(srv, args):
        args.pop(0)
        if len(args):
            name = args.pop(0)
        else:
            name = repr(srv.obj.task)
        from amoco.db import sql, EmuData, session

        if name.startswith("#"):
            try:
                id_ = int(name[1:])
            except ValueError:
                srv.msgs.put("bad #id ?")
                return 0
            else:
                # get Emudata object:
                res = session.get(EmuData, id_)
        else:
            req = sql.select(EmuData).where(EmuData.name == name)
            # get list of all EmuData objects:
            res = session.execute(req).scalars().all()
            if len(res) == 1:
                res = res[0]
        if isinstance(res, EmuData):
            srv.obj.from_db(res)
            srv.msgs.put(repr(res))
        else:
            srv.msgs.put("use cmd 'restore #id' to select one entry below:")
            for r in res:
                srv.msgs.put(f"#{r.id}: {r.cur}".format(r=r))
        # wait for new command (don't quit client loop):
        return 0


# -----------------------------------------------------------------------------


@DefineSrvCommand(srv, "eval", ["p", "set"])
class cmd_eval(object):
    """eval/p EXPR: evaluate python amoco EXPR in task context.
    The 'set' command allows for modifying the current state by setting a
    right-value EXPR to a left-value location EXPR where the separator
    is the symbol '='. For example 'set zf = 1'.

    objects that can be accessed are:
    - state (global mapper that represents the current cpu state)
    - OS
    - task
    and functions/methods:
    - memory (view)
    - getx(x, size): fetch size *bits* at memory address x
    - setx(x, val, size): store val[0:size] at memory address x
    """

    @staticmethod
    def glob(srv):
        if srv.obj:
            glob = {}
            glob.update(vars(srv.obj))
            if "task" in glob:
                glob.update(vars(srv.obj.task.cpu))
                glob["OS"] = srv.obj.task.OS
                glob["state"] = srv.obj.task.state
                glob["memory"] = srv.obj.task.view.memory
                glob["getx"] = srv.obj.task.getx
                glob["setx"] = srv.obj.task.setx
        else:
            from amoco.cas import expressions

            glob = vars(expressions)
        return glob

    @staticmethod
    def expr(srv, args):
        # args: should be arguments list without the leading command
        x = " ".join(args)
        try:
            res = eval(x, cmd_eval.glob(srv))
        except Exception as e:
            res = "eval error: %s" % e
        return res

    @staticmethod
    def expr_set(srv, p):
        # separate left/right lists of p:
        l, r = [x.split() for x in p.split("=", 1)]
        lx = cmd_eval.expr(srv, l)
        rx = cmd_eval.expr(srv, r)
        return (lx, rx)

    def run(self, srv, args):
        cmd = args.pop(0)
        try:
            if cmd == "set":
                lx, rx = cmd_eval.expr_set(srv, " ".join(args))
                # actually set lx to rx:
                srv.obj.task.setx(lx, rx)
                srv.msgs.put("%s <- %s" % (lx, rx))
                return 0
            expr = self.expr(srv, args)
            srv.msgs.put(str(expr))
        except ValueError as e:
            srv.msgs.put("error: %s" % e)
        return 0


# -----------------------------------------------------------------------------


@DefineSrvCommand(srv, "hexdump", ["hd", "dq", "dd", "dw", "db"])
class cmd_hexdump(object):
    """hexdump/hd [EXPR [(nbl,nbc)]]

    For shortcuts dq/dd/dw/db,
    display memory at address EXPR, as array of bytes (db),
    shorts (dw), 32 bits integers (dd) or 64 bits integers (dq)
    with nbl lines and nbc columns (defaults to (16, 16)).

    For hexdump/hd command, display memory at address EXPR as an
    hexdump output with nbl lines and nbc columns of bytes along with
    their ASCII representation. Any symbolic entry is outputed
    as '??'.
    """

    def __init__(self):
        self.last_args = None
        self.w = {"dq": (64, 2), "dd": (32, 4), "dw": (16, 8), "db": (8, 16)}

    def run(self, srv, args):
        cmd = args.pop(0)
        if len(args) > 0:
            x = args.pop(0)
            addr = eval(x, cmd_eval.glob(srv))
            # set default nbl,nbc,w:
            nbl = 16
            w, nbc = self.w.get(cmd, (None, 16))
            # check for (nbl,nbc) modifier:
            if len(args) > 0:
                args = "".join(args)
                try:
                    nbl, nbc = re.findall("\((\d+),(\d+)\)", args)[0]
                except Exception:
                    srv.msgs.put(
                        "exception in hexdump command arguments, using (%d,%d)"
                        % (nbl, nbc)
                    )
                nbl = int(nbl)
                nbc = int(nbc)
        elif srv.lastcmd == cmd:
            addr, nbl, nbc, w = self.last_args
            addr = addr + (nbl * nbc * (w // 8))
        else:
            logger.warning("default arg in cmd %s" % cmd)
            srv.msgs.put(self.__class__.__doc__)
            return 0
        self.last_args = (addr, nbl, nbc, w)
        vlt = srv.obj.task.view.memory(addr, nbl, nbc, w)
        srv.msgs.put(srv.obj.task.view.engine.highlighted(vlt))
        return 0


# -----------------------------------------------------------------------------


@DefineSrvCommand(srv, "strings", ["ds"])
class cmd_strings(object):
    """strings/ds [EXPR [size]]

    display strings starting at address EXPR, up to EXPR+size, or first
    string if size is not provided.
    """

    def run(self, srv, args):
        cmd = args.pop(0)
        if len(args) > 0:
            x = args.pop(0)
            addr = eval(x, cmd_eval.glob(srv))
            sz = None
            if len(args) > 0:
                x = "".join(args)
                try:
                    size = eval(x, cmd_eval.glob(srv))
                    sz = int(size)
                except Exception:
                    srv.msgs.put("strings: bad arguments")
        else:
            logger.warning("default arg in cmd %s" % cmd)
            srv.msgs.put(self.__class__.__doc__)
            return 0
        vlt = srv.obj.task.view.strings(addr, size=sz)
        srv.msgs.put(srv.obj.task.view.engine.highlighted(vlt))
        return 0


# -----------------------------------------------------------------------------


@DefineSrvCommand(srv, "display", ["dt"])
class cmd_display(object):
    """display/dt EXPR typename

    display memory at address EXPR as an instance of typename,
    where typename is searched in the ccrawl database with the same name
    as the current program's binary, and with ".db" extension or the default
    database provided by configuration.
    """

    def __init__(self):
        from ccrawl import main as cc

        self.last_args = None
        self.c = cc.conf.config = cc.conf.Config()
        self.cc = cc
        self.cache = {}

    def run(self, srv, args):
        cmd = args.pop(0)
        if len(args) != 2:
            logger.warning("bad args in cmd %s" % cmd)
            srv.msgs.put("usage is 'display/dt EXPR typename'")
            return 0
        x = args.pop(0)
        w = srv.obj.task.cpu.getPC().size
        addr = eval(x, cmd_eval.glob(srv))
        if isinstance(addr, int):
            addr = srv.obj.task.cpu.cst(addr, w)
        tname = args.pop(0)
        if tname in self.cache:
            axt = self.cache[tname]
        else:
            self.c.Database.local = srv.obj.task.bin.filename + ".db"
            self.c.Database.localonly = True
            db = self.cc.Proxy(self.c.Database)
            Q = self.cc.where("id") == tname
            if db.contains(Q):
                l = db.get(Q)
                x = self.cc.ccore.from_db(l)
                from ccrawl.ext.amoco import build

                axt = build(x, db)
                self.cache[tname] = axt
            else:
                srv.msgs.put(
                    "type '%s' not found in database (%s)"
                    % (tname, self.c.Database.local)
                )
                return 0
        self.last_args = (addr, tname)
        target = srv.obj.task.state(addr)
        data = srv.obj.task.read_data(target, axt.size())[0]
        expr = axt().unpack(data, psize=w // 8)
        srv.msgs.put(str(expr))
        return 0


# -----------------------------------------------------------------------------


@DefineSrvCommand(srv, "disasm", ["di"])
class cmd_disasm(object):
    """disasm/di [EXPR]: disassemble instructions at memory address EXPR."""

    def __init__(self):
        self.iterator = None
        self.lastx = ""

    def run(self, srv, args):
        cmd = args.pop(0)
        x = " ".join(args)
        if x:
            if srv.lastcmd != cmd or self.lastx != x:
                self.lastx = x
                addr = eval(x, cmd_eval.glob(srv))
                if self.iterator is not None:
                    self.iterator.close()
                self.iterator = srv.obj.sa.iterblocks(addr)
        elif srv.lastcmd != cmd:
            if self.iterator is not None:
                # disasm from PC address
                self.iterator.close()
            self.iterator = srv.obj.sa.iterblocks()
        try:
            expr = str(next(self.iterator).view)
        except (TypeError, StopIteration, RuntimeError):
            expr = "block generator has stopped"
            logger.verbose("end of cmd %s" % cmd)
            self.iterator = None
        srv.msgs.put(expr)
        return 0


# -----------------------------------------------------------------------------


@DefineSrvCommand(srv, "header")
class cmd_header(object):
    "header: pretty-print the task binary header (ELF/PE/Mach-O/COFF/...)."

    @staticmethod
    def run(srv, args):
        cmd = args.pop(0)
        if srv.obj:
            try:
                t = srv.obj.task
            except AttributeError:
                t = srv.obj
            srv.msgs.put(str(t.view.header))
        else:
            logger.error("error in cmd %s" % cmd)
            srv.msgs.put("error: no task loaded")
        return 0


# -----------------------------------------------------------------------------


@DefineSrvCommand(srv, "context", ["ctx"])
class cmd_context(object):
    "context/ctx: show the selected emulator view frames (bin,regs,code,stack)."

    @staticmethod
    def run(srv, args):
        cmd = args.pop(0)
        if srv.obj:
            srv.msgs.put(str(srv.obj.view))
        else:
            logger.error("error in cmd %s" % cmd)
            srv.msgs.put("error: no task loaded")
        return 0


# -----------------------------------------------------------------------------


@DefineSrvCommand(srv, "stepi", ["si"])
class cmd_stepi(object):
    """
    stepi/si: step one instruction. (Note that breakpoints and watchpoints
    are ignored when stepping.)
    """

    @staticmethod
    def run(srv, args):
        cmd = args.pop(0)
        if srv.obj:
            srv.obj.stepi()
            srv.msgs.put(str(srv.obj.view))
        else:
            logger.error("error in cmd %s" % cmd)
            srv.msgs.put("error: no task loaded")
        return 0


# -----------------------------------------------------------------------------


@DefineSrvCommand(srv, "nexti", ["ni"])
class cmd_nexti(object):
    """
    nexti/ni: break on next listing instruction (and remove breakpoint.)
    """

    @staticmethod
    def run(srv, args):
        if srv.obj:
            cur = srv.obj.block_cur.instr[0]
            target = cur.address + cur.length
            srv.obj.breakpoint(target)
            cmd_continue.run(srv, args)
            srv.obj.hooks.pop()
        else:
            srv.msgs.put("error: no task loaded")
        return 0


# -----------------------------------------------------------------------------


@DefineSrvCommand(srv, "until", ["u"])
class cmd_until(object):
    """
    until/u: break on given address/expression/instruction's property
             (and remove breakpoint.)
    """

    @staticmethod
    def run(srv, args):
        cmd = args.pop(0)
        if srv.obj:
            srv.obj.breakpoint(cmd_eval.expr(srv, args))
            cmd_continue.run(srv, args)
            srv.obj.hooks.pop()
        else:
            logger.error("error in cmd %s" % cmd)
            srv.msgs.put("error: no task loaded")
        return 0


# -----------------------------------------------------------------------------


@DefineSrvCommand(srv, "continue", ["c"])
class cmd_continue(object):
    """
    continue/c: continue until a breakpoint or watchpoint.
    """

    @staticmethod
    def run(srv, args):
        cmd = args.pop(0)
        if srv.obj:
            count = 0
            group = 1000
            t0 = time.time()
            with rp.Progress(
                rp.SpinnerColumn(),
                rp.TextColumn("[progress.description]{task.description}"),
                rp.TimeElapsedColumn(),
                console=logger.handlers[0].console,
                expand=True,
            ) as bar:
                tid = bar.add_task("count:%08dk  perf:%2.4f KHz" % (0, 0), total=None)
                for i in srv.obj.iterate():
                    count += 1
                    if count % group == 0:
                        t = time.time()
                        avrg = (t - t0) / count
                        freq = (1.0 / avrg) / group
                        bar.update(
                            tid,
                            description="count:%08dk  perf:%2.4f KHz"
                            % (count // group, freq),
                        )
            t = time.time()
            srv.msgs.put("count: %08d  time: %2.5f s  " % (count, (t - t0)))
            srv.msgs.put(str(srv.obj.view))
        else:
            logger.error("error in cmd %s" % cmd)
            srv.msgs.put("error: no task loaded")
        return 0


# -----------------------------------------------------------------------------


@DefineSrvCommand(srv, "log")
class cmd_log(object):
    """
    log [COUNT]: log instructions and operand values while continuing emulation until
    a breakpoint or watchpoint is reached or until COUNT instructions have been emulated
    if provided.
    """

    @staticmethod
    def run(srv, args):
        cmd = args.pop(0)
        if srv.obj:
            count = 0
            limit = None
            if args:
                try:
                    limit = int(args.pop(0), 0)
                except Exception:
                    logger.warning("cmd_log: bad argument (ignored)")
            for i, ops in srv.obj.iterate(trace=True):
                count += 1
                ops_v = ["%s (%s)" % (v, o) for v, o in ops]
                logger.info(
                    "%08x: %s %s"
                    % (i.address, "{: <8}".format(i.mnemonic.lower()), ", ".join(ops_v))
                )
                if count >= limit:
                    break
            srv.msgs.put("logged %d instruction in server's log (INFO level)" % count)
        else:
            logger.error("error in cmd %s" % cmd)
            srv.msgs.put("error: no task loaded")
        return 0


# -----------------------------------------------------------------------------


@DefineSrvCommand(srv, "trace", ["tr"])
class cmd_trace(object):
    """
    trace/tr EXPR [{actions}] [# filename]: insert a tracepoint that will trigger
    actions upon EXPR.

    If EXPR is a constant (or evaluates to a constant), the trace condition
    is assumed to be "pc == EXPR".
    If EXPR is an amoco expression, the trace condition is EXPR.

    {actions} is a list of directives separated by ';'. Each directives is either
    an 'eval' or a 'set' command. If no actions are defined, the entire state is
    printed to a file.

    filename is an optional filename where directives (or the full state) are printed.
    If not provided, stdout is used for any defined directives while a temporary file is
    created if the full state is printed.
    """

    @staticmethod
    def run(srv, args):
        cmd = args.pop(0)
        if srv.obj:
            if len(args) > 0:
                l = " ".join(args)
                m = re.search("([^{#]*)([{].*[}])?\s*(#.*)?", l)
                x = cmd_eval.expr(srv, [m.group(1).strip()])
                if (actions := m.group(2)) is not None:
                    act = []
                    # remove '{' and '}':
                    actions = actions.translate({123: 32, 125: 32}).strip()
                    # append each action:
                    for a in actions.split(";"):
                        a = a.strip()
                        if a.startswith("set "):
                            act.append(cmd_eval.expr_set(srv, a[4:]))
                        elif a.startswith("eval "):
                            act.append((cmd_eval.expr(srv, a[5:].split()), None))
                else:
                    act = None
                if (filename := m.group(3)) is not None:
                    filename = filename.replace("#", "").strip()
                    file = open(filename, "a")
                else:
                    file = None
                res = srv.obj.tracepoint(x, act, file)
                srv.msgs.put(str(res))
            else:
                res = srv.obj.tracepoint()
                srv.msgs.put(res)
        else:
            logger.error("error in cmd %s" % cmd)
            srv.msgs.put("error: no task loaded")
        return 0


# -----------------------------------------------------------------------------


@DefineSrvCommand(srv, "break", ["b"])
class cmd_break(object):
    """
    break/b EXPR: insert breakpoint associated to EXPR.

    If EXPR is a constant (or evaluates to a constant), the break condition
    is assumed to be "pc == EXPR".
    If EXPR is an amoco expression, the break condition is EXPR.
    This allows to break on any *state* condition like "eax + ebx == 3".
    If EXPR is a JSON-formated string i.{'mnemonic':'...',
                                         'dst':'...',
                                         'src':'...'} the break occurs on
    any instruction matching mnemonic (from cpu's spec) and/or dst and/or
    src operands symbolic expressions.
    """

    @staticmethod
    def run(srv, args):
        cmd = args.pop(0)
        if srv.obj:
            if args:
                if len(args) == 1 and args[0].startswith("i."):
                    kargs = cmd_eval.expr(srv, [args[0][2:]])
                    res = srv.obj.ibreakpoint(**kargs)
                else:
                    res = srv.obj.breakpoint(cmd_eval.expr(srv, args))
                srv.msgs.put(str(res))
            else:
                res = srv.obj.breakpoint()
                srv.msgs.put(res)
        else:
            logger.error("error in cmd %s" % cmd)
            srv.msgs.put("error: no task loaded")
        return 0


# -----------------------------------------------------------------------------


@DefineSrvCommand(srv, "watch", ["w"])
class cmd_watch(object):
    """
    watch/w EXPR: insert watchpoint associated to EXPR.

    The instruction iterator will break if EXPR changes.
    If EXPR is a constant (or evaluates to a constant), the watch condition
    is assumed to be "mem(EXPR,8)".
    If EXPR is an amoco expression, the watch condition is EXPR.
    This allows to watch any *state* condition like "eax + ebx".
    The iterator will break if the watch condition evaluation changes from
    the value it had when the watchpoint was created.
    """

    @staticmethod
    def run(srv, args):
        cmd = args.pop(0)
        if srv.obj:
            if args:
                res = srv.obj.watchpoint(cmd_eval.expr(srv, args))
                srv.msgs.put(str(res))
            else:
                res = srv.obj.watchpoint()
                srv.msgs.put(res)
        else:
            logger.error("error in cmd %s" % cmd)
            srv.msgs.put("error: no task loaded")
        return 0


# -----------------------------------------------------------------------------


@DefineSrvCommand(srv, "clear", ["cl"])
class cmd_clear(object):
    """
    clear/cl INDEX: remove breakpoint or watchpoint hook number INDEX.

    If INDEX is "all", then removes every hook.
    """

    @staticmethod
    def run(srv, args):
        cmd = args.pop(0)
        if srv.obj:
            if args:
                index = args.pop(0)
                if index.lower() == "all":
                    srv.obj.hooks = []
                    return 0
                if 0 <= int(index, 0) < len(srv.obj.hooks):
                    res = srv.obj.hooks.pop(int(index, 0)).__doc__
                else:
                    res = "no hook at index %s ??" % index
                srv.msgs.put(str(res))
            else:
                srv.msgs.put("clear what?")
        else:
            logger.error("error in cmd %s" % cmd)
            srv.msgs.put("error: no task loaded")
        return 0


# -----------------------------------------------------------------------------


@DefineSrvCommand(srv, "checksec")
class cmd_checksec(object):
    "checksec: security parameters related to the current task."

    @staticmethod
    def run(srv, args):
        if srv.obj:
            v = srv.obj.task.view
            srv.msgs.put(str(v.engine.highlighted(v.checksec)))
        else:
            srv.msgs.put("error: no task loaded")
        return 0


# -----------------------------------------------------------------------------


@DefineSrvCommand(srv, "debug")
class cmd_debug(object):
    "debug: start a pdb debugger on current instruction."

    @staticmethod
    def run(srv, args):
        if srv.obj:
            import pdb

            i = srv.obj.block_cur.instr[0]
            pdb.runcall(i, srv.obj.task.state)
        else:
            srv.msgs.put("error: no task loaded")
        return 0


# -----------------------------------------------------------------------------
