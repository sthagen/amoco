# -*- coding: utf-8 -*-

# This code is part of Amoco
# Copyright (C) 2016-2020 Axel Tillequin (bdcht3@gmail.com)
# published under GPLv2 license

"""
views.py
========

This module implements the high-level (engines agnostic) views that
allow to display various amoco objects according to the underlying
graphics Engine that is loaded (see :mod:`amoco.ui.graphics`).

All views inherit from the same :class:`View` class and then
specializes their :meth:`_vltable` method to transform an amoco object
into a table of rows of Tokens which in turn can be used by the loaded
engine to instanciate the graphics.

The default engine :mod:`amoco.ui.graphics.term` has no specific
graphic objects and just returns its vltable for pretty printing
using the pygments package.
"""

import re

from amoco.config import conf
from amoco.logger import Log

logger = Log(__name__)
logger.debug("loading module")

from amoco.cas.expressions import regtype, et_vrb
from amoco.ui.graphics import Engine
from amoco.ui.render import Token, vltable, tokenrow, icons


# -------------------------------------------------------------------------------


class View(Engine):
    """
    Base class that implements common API for all views.

    A view represents an amoco element (either a block, a map, a function, ...)
    as a positionable "boxed" object, ie an object with (width,height) and (x,y)
    coords. A view is bound to the configured graphics engine through its parent
    Engine class and offers a common API to display the amoco element.

    Args:
        of: the amoco element associated with this view.

    Attributes:
        of: the amoco element associated with this view.
        obj: the engine's graphic object that represents the amoco element.
             This is a lazy constructed object that calls the engine's builder
             upon first attribute access. Hence, the object is never constructed
             until it is used for the first time.
        w: the width of the view.
        h: the height of the view.
        xy (tuple[int]): the (x,y) coords of the view.

    Methods:
        __str__ (str): a pretty-printed string that represents the element.
    """

    def __init__(self, of=None):
        self.of = of

    @property
    def obj(self):
        try:
            return self._obj
        except AttributeError:
            self._obj = self.engine.builder(self)
            return self._obj

    def setw(self, w):
        self.engine.setw(self, w)

    def getw(self):
        return self.engine.getw(self)

    w = property(getw, setw)

    def seth(self, h):
        self.engine.seth(self, h)

    def geth(self):
        return self.engine.geth(self)

    h = property(geth, seth)

    def setxy(self, xy):
        self.engine.setxy(self, xy)

    def getxy(self):
        return self.engine.getxy(self)

    xy = property(getxy, setxy)

    def __str__(self):
        return self.engine.pp(self)

    def __rich__(self):
        return self.engine.RichTable(self._vltable())


# -------------------------------------------------------------------------------


class StructView(View):
    """
    This class implements the view for all structures that inherit from
    :class:`system.structs.StructFormatter` objects.

    A StructView specializes :class:`View` by implementing the _vltable method
    which allows to pretty print (with engines' pp) each of the structure's field
    name and value according to special token formatters defined within the
    StructFormatter class.
    """

    def _vltable(self, **kargs):
        t = vltable(**kargs)
        cname = self.__class__.__name__
        t.header = "{%s}" % cname
        for f in self.fields:
            if f.name and f.name != "_":
                tv = self.fmtkey(f.name)
                tv.rows[0].addcolumn(0, [(Token.Literal, f.name)])
                tv.rows[0].addcolumn(1, [(Token.Literal, ": ")])
                for r in tv.rows[1:]:
                    r.addcolumn(0, [(Token.Literal, " ")])
                    r.addcolumn(1, [(Token.Literal, " ")])
                t.rows.extend(tv.rows)
            elif hasattr(f, "subnames"):
                subn = filter(lambda n: n != "_", f.subnames)
                for n in subn:
                    tv = self.fmtkey(n)
                    tv.rows[0].addcolumn(0, [(Token.Literal, n)])
                    tv.rows[0].addcolumn(1, [(Token.Literal, ": ")])
                    for r in tv.rows[1:]:
                        r.addcolumn(0, [(Token.Literal, " ")])
                        r.addcolumn(1, [(Token.Literal, " ")])
                    t.rows.extend(tv.rows)
            else:
                continue
        t.update()
        return t


# -------------------------------------------------------------------------------


class dataView(View):
    """
    This class implements the view for :class:`system.core.DataIO` objects.

    A dataView specializes :class:`View` by implementing the _vltable method
    which allows to pretty print (with engines' pp) the hexdump of the
    associated DataIO object (ie file/stream bytes.)

    Args:
        of: the DataIO to be viewed.

    Attributes:
        cur: the current byte offset in the DataIO
        nbb: the number of bytes per line in the view
        nbl: the number of lines in the view
    """

    def __init__(self, dataio):
        super().__init__(of=dataio)
        self.cur = 0
        self.nbb = 16
        self.nbl = 16

    def hexdump(self, cur=None, nbb=None, nbl=None):
        """
        Output the vltable of the hexdump of the DataIO from
        cur offset with nbl lines of nbb bytes.
        """
        if cur is None:
            cur = self.cur
        if nbb is None:
            nbb = self.nbb
        if nbl is None:
            nbl = self.nbl
        self.cur = cur
        self.nbb = nbb
        self.nbl = nbl
        t = vltable()
        t.header = "hexdump"
        t.rowparams["sep"] = icons.sep
        for l in range(self.nbl):
            r = [(Token.Address, "%08x" % self.cur), (Token.Column, "")]
            data = self.of[self.cur : self.cur + self.nbb]
            if isinstance(data, bytes):
                s = " ".join("%02x" % d for d in data)
            else:
                s = []
                for d in data:
                    if isinstance(d, bytes):
                        s.append(" ".join("%02x" % x for x in d))
                    else:
                        s.append(" ".join(["??"] * d.length))
                s = " ".join(s)
            # add extra space
            s = s[0:23] + " " + s[23:]
            r.append((Token.Literal, s))
            r.append((Token.Column, ""))
            B = []
            for x in filter(None, s.split(" ")):
                v = 0 if "?" in x else int(x, 16)
                if 32 <= v <= 127:
                    B.append(chr(v))
                else:
                    B.append(".")
            s = "".join(B)
            r.append((Token.Literal, s))
            self.cur += self.nbb
            t.addrow(r)
        return t

    def _vltable(self, **kargs):
        t = vltable(**kargs)
        t.rowparams["sep"] = icons.sep
        # TODO wanted output:
        # binwalk stuff, entropy, IC, histogram(s), ...
        return t


# -------------------------------------------------------------------------------


class blockView(View):
    """
    This class implements the view for :class:`code.block` objects.

    A blockView specializes :class:`View` by implementing the _vltable method
    which allows to pretty print the block instructions with pygments' highlight
    or to rely on the underlying engine to build a graphic object from this table.
    """

    def __init__(self, block):
        super().__init__(of=block)

    @staticmethod
    def instr(i, flavor=None):
        """
        Helper function that returns a list of tokens for the provided instr
        with additional columns like the address of the instruction and optionally
        also its bytecode.
        """
        ins2 = i.toks()
        if isinstance(ins2, str):
            ins2 = [(Token.Literal, ins2)]
        try:
            b = "'%s'" % ("".join(["%02x" % x for x in bytes(i.bytes)]))
        except TypeError:
            b = "'%s'" % ("--" * (i.length))
        ins = [
            (Token.Address, "{}".format(str(i.address))),
            (Token.Column, ""),
        ]
        if conf.Code.bytecode:
            ins.extend([(Token.Literal, b), (Token.Column, "")])
        T = []
        for t, v in ins + ins2:
            if flavor and t != Token.Column:
                t = getattr(t, flavor)
            T.append((t, v))
        return T

    def _vltable(self, **kargs):
        """
        Returns the vltable from instructions' of the block with additional
        header/footer, address and possibly bytecode.
        """
        T = vltable(**kargs)
        for i in self.of.instr:
            T.addrow(self.instr(i))
        if conf.Code.bytecode:
            pad = conf.Code.padding
            T.colsize[1] += pad
        if conf.Code.header:
            T.header = "block %s" % self.of.address
        if conf.Code.footer:
            T.footer = "%d instructions" % len(self.of.instr)
        return T


# -------------------------------------------------------------------------------


class mapperView(View):
    """Class that implements view of mapper objects.
    A mapperView additionnally implements the _vltable method which allows to
    pretty print the map through ui.render.highlight method.
    The str() representation of a mapperView instance uses this pretty printer
    through engines' pp method.
    """

    def __init__(self, m):
        super().__init__(of=m)

    def _vltable(self, **kargs):
        t = vltable(**kargs)
        t.rowparams["sep"] = icons.lar
        for l, v in self.of:
            if l._is_reg:
                if l.etype & regtype.FLAGS:
                    t.addrow(l.toks(**kargs) + [(Token.Literal, ":")])
                    for pos, sz in l._subrefs:
                        t.addrow(
                            [(Token.Literal, icons.sep)]
                            + l[pos : pos + sz].toks(**kargs)
                            + [(Token.Column, "")]
                            + v[pos : pos + sz].toks(**kargs)
                        )
                    continue
                v = v[0 : v.size]
            lv = l.toks(**kargs) + [(Token.Column, "")] + v.toks(**kargs)
            t.addrow(lv)
        return t


# -------------------------------------------------------------------------------


class mmapView(View):
    """Class that implements view of MemoryMap objects.
    A mmapView implements the _vltable method for engines' pretty printer (pp).
    """

    def __init__(self, m):
        super().__init__(of=m)

    def _vltable(self, **kargs):
        t = vltable(**kargs)
        t.rowparams["sep"] = icons.sep
        for k, z in self.of._zones.items():
            if k is None:
                a = ""
            else:
                a = str(k)
            for o in z._map:
                lv = []
                lv.append((Token.Address, "%s%+08x" % (a, o.vaddr)))
                lv.append((Token.Column, ""))
                data = str(o.data)
                if len(data) > 16:
                    data = data[:16] + icons.dots
                lv.append((Token.Literal, data))
                lv.append((Token.Column, ""))
                lv.append((Token.Address, ".%+08x" % (o.end)))
                t.addrow(lv)
            t.addrow([(Token.Memory, icons.hor * 8)])
        return t


# -------------------------------------------------------------------------------


class funcView(View):
    """Class that implements view of func objects.
    A funcView additionnally implements the _vltable method which allows to
    pretty print the function through engines' pp method.
    """

    def __init__(self, func):
        from grandalf.layouts import SugiyamaLayout

        super().__init__(of=func)
        self.layout = SugiyamaLayout(func.cfg)

    def _vltable(self, **kargs):
        t = vltable(**kargs)
        w = t.width
        th = "[func %s, signature: %s]"
        t.header = (th % (self.of, self.of.sig())).ljust(w, icons.hor)
        for b in self.of.blocks():
            t.rows.extend(b.view.rows)
        t.footer = icons.hor * w
        t.update()
        return t


# -------------------------------------------------------------------------------


class xfuncView(View):
    """Class that implements view for "external" functions."""

    def __init__(self, xfunc):
        super().__init__(of=xfunc)

    def _vltable(self, **kargs):
        t = vltable(**kargs)
        w = t.width
        th = "[xfunc %s, signature: %s]"
        t.header = (th % (self.of, self.of.sig())).ljust(w, icons.hor)
        t.footer = icons.hor * w
        return t


# -------------------------------------------------------------------------------


class execView(View):
    """Class that implements view of objects that inherit from CoreExec (tasks).
    An execView additionnally implements the _vltable method which allows to
    pretty print various tasks' properties or expressions' from current state.
    """

    def __init__(self, of):
        super().__init__(of)

    def _vltable(self, **kargs):
        return self.title()

    def title(self, header="", more=None):
        t = vltable()
        t.header = header
        t.rowparams["sep"] = icons.tri
        t.rowparams["wrap"] = False
        name = self.of.__module__
        if name.endswith("__main__"):
            name = self.of.__class__.__name__
        t.addrow(
            [
                (Token.Column, ""),
                (Token.String, self.of.bin.filename),
                (Token.Column, ""),
                (Token.Address, self.of.bin.__class__.__name__),
                (Token.Column, ""),
                (Token.Address, name),
            ]
        )
        if not more and hasattr(self.of, "title_info"):
            more = [(Token.Alert, x) for x in self.of.title_info()]
        if more:
            r = t.rows[0]
            for x in more:
                r.cols[-1].append((Token.Column, ""))
                r.cols.append([x])
            t.update()
        return t

    @property
    def header(self):
        return self.of.bin.header

    @property
    def checksec(self):
        if hasattr(self.of.bin, "checksec"):
            t = vltable()
            t.rowparams["sep"] = icons.sep
            s = self.of.bin.checksec()

            def tokattr(v):
                return Token.Good if v else Token.Alert

            r = []
            for k, v in s.items():
                r.append((tokattr(v), "%s: %s" % (k, v)))
                r.append((Token.Column, ""))
            r.pop()
            t.addrow(r)
        else:
            t = ""
        return t

    def registers(self, header=""):
        t = vltable()
        t.header = header
        if hasattr(self.of.cpu, "registers"):
            t.rowparams["sep"] = ": "
            for _r in self.of.cpu.registers:
                if _r.etype & regtype.FLAGS:
                    if _r._is_slc:
                        sta, sto = _r.pos, _r.pos + _r.size
                        _r = _r.x
                    else:
                        sta, sto = 0, _r.size
                    val = [(Token.Literal, "[ ")]
                    for pos, sz in _r._subrefs:
                        if (sta <= pos < sto) and (sz < (sto - sta)):
                            _s = _r[pos : pos + sz]
                            val.extend(_s.toks())
                            val.append((Token.Literal, ":"))
                            val.extend(self.of.state(_s).toks())
                            val.append((Token.Literal, icons.sep))
                    val.pop()
                    val.append((Token.Literal, " ]"))
                elif not _r.etype & regtype.OTHER:
                    val = self.of.state(_r).toks()
                else:
                    val = None
                if val:
                    t.addrow(_r.toks() + [(Token.Column, "")] + val)
        return t

    def memory(self, start, nbl=1, nbc=1, w=None):
        t = vltable()
        t.header = "memory"
        t.rowparams["sep"] = " "
        aw = self.of.cpu.getPC().size
        if isinstance(start, int):
            start = self.of.cpu.cst(start, size=aw)
        if w is None:
            if start._is_cst:
                dv = dataView(self.of.state.mmap)
                try:
                    cur = self.of.cpu.mmu_get_paddr(self.of.state, start.v)
                except (AttributeError, MemoryError):
                    cur = start.v
                return dv.hexdump(cur, nbl, nbc)
            else:
                logger.warning("hexdump: start address not a cst? (%s)" % start)
                return t
        if hasattr(start, "etype"):
            if start._is_mem:
                cur = start
            else:
                cur = self.of.cpu.mem(start, size=w)
        for i in range(nbl):
            r = cur.a.toks() + [(Token.Column, ""), (Token.Literal, icons.ver + " ")]
            for j in range(nbc):
                try:
                    r.extend(self.of.state(cur).toks())
                except MemoryError:
                    t.addrow(r)
                    return t
                r.append((Token.Column, ""))
                cur.a.disp += w // 8
            r.pop()
            t.addrow(r)
        return t

    def strings(self, start, size=None):
        t = vltable()
        t.header = "strings"
        t.rowparams["sep"] = " "
        aw = self.of.cpu.getPC().size
        if isinstance(start, int):
            start = self.of.cpu.cst(start, size=aw)
        if start._is_cst:
            try:
                cur = self.of.cpu.mmu_get_paddr(self.of.state, start.v)
            except AttributeError:
                cur = start.v
        else:
            logger.warning("strings: start address not a cst? (%s)" % start)
            return t
        s = b""

        def concretize(data):
            res = b""
            for x in data:
                if isinstance(x, bytes):
                    res += x
                else:
                    res += b"\0" * x.length
            return res

        while s.find(b"\0") == -1:
            s += concretize(self.of.state.mmap.read(cur, size or 256))
            if size:
                break
            else:
                cur += 256
        if size is None:
            s = s[: s.find(b"\0") + 1]
        pos = 0
        while pos < len(s):
            r = [(Token.Address, str(start + pos)), (Token.Column, "")]
            npos = s.find(b"\0", pos)
            if npos == -1:
                npos = len(s)
            ss = s[pos : npos + 1]
            if len(ss) > 0:
                r.extend(
                    [(Token.String, ss), (Token.Column, ""), (Token.Constant, len(ss))]
                )
            pos = npos + 1
            t.addrow(r)
        return t

    def code(self, blk):
        """
        Enhance a code block with info from the task/OS.
        This allows any symbol associated with an address/constant to
        be displayed as comment, optionally adds the segment name
        (ie ELF section name) to the location if found.
        """
        if not isinstance(blk, vltable):
            T = blk.view._vltable()
        else:
            T = blk
        for i, r in enumerate(T.rows):
            for c in r.cols[2:]:  # skip address and bytecode columns
                address = int(r.cols[0][0][1], 0)
                if name := self.of.symbol_for(address):
                    r.label = (Token.Name, name)
                for i in range(len(c) - 1, -1, -1):
                    tn, tv = c[i]
                    # we take 1st level token id. For example,
                    # Token.Address.Mark is reduced to Token.Address
                    tn = tn.split()
                    use_Mark = ".Mark" in str(tn)
                    tn = tn[1]
                    if tn == Token.Memory:
                        tn = Token.Address
                        tv = re.findall(r"(0x[0-9a-zA-Z]+)", tv)
                        if len(tv) == 1:
                            tv = tv[0]
                        else:
                            continue
                    if tn in (Token.Address, Token.Constant):
                        try:
                            v = int(tv, 0)
                            tv = self.of.symbol_for(v)
                        except ValueError:
                            tv = None
                        if tv:
                            if use_Mark:
                                tn = Token.Comment.Mark
                            else:
                                tn = Token.Comment
                            c.insert(i + 1, (tn, tv))
            if conf.Code.segment:
                try:
                    segname = self.of.segment_for(address)
                except ValueError:
                    segname = None
                if segname:
                    if use_Mark:
                        tn = Token.Segment.Mark
                    else:
                        tn = Token.Segment
                    r.cols[0].insert(1, (tn, segname))
        T.update()
        if len(T.rows) > conf.Code.lines:
            T.rows = T.rows[: conf.Code.lines]
            T.addrow([(Token.Literal, icons.dots)])
        if conf.Code.bytecode:
            pad = conf.Code.padding
            T.colsize[1] += pad
        if T.header:
            T.header = T.header
        if T.footer:
            T.footer = T.footer
        return T


# -------------------------------------------------------------------------------


class emulView(View):
    """
    An emulView implements the view for amoco.emu.emul instances.
    It defines its own __str__ as a series of "frames" with pretty printed
    vtables build from other views.
    """

    def __init__(self, of, frames=None):
        super().__init__(of)
        if frames is None:
            frames = [
                self.frame_bin,
                self.frame_callstack,
                self.frame_regs,
                self.frame_code,
                self.frame_stack,
            ]
        self.frames = frames

    def frame_bin(self):
        return self.of.task.view.title("[ bin ]")

    def frame_regs(self):
        return self.of.task.view.registers("[ regs ]")

    def frame_code(self):
        here = self.of.task.state(self.of.pc)
        T = vltable()
        flavor = None
        blk = self.of.sa.iterblocks()
        try:
            b = next(blk)
        except StopIteration:
            b = None
            logger.warning("no block at address %s" % here)
        else:
            nextb = None
            try:
                nextb = next(blk)
            except StopIteration:
                logger.warning("end of blocks?")
            blk.close()
        self.of.block_cur = b
        self.of.block_nxt = nextb
        if b is not None:
            delay_slot = False
            for i in b.instr:
                if i.address == here:
                    flavor = "Mark"
                    if i.misc.get("delayed", False):
                        delay_slot = True
                elif delay_slot:
                    flavor = "Mark"
                    delay_slot = False
                else:
                    flavor = None
                T.addrow(blockView.instr(i, flavor))
            if nextb is not None:
                for i in nextb.instr:
                    if len(T.rows) > (conf.Code.lines - conf.Code.hist):
                        break
                    T.addrow(blockView.instr(i))
        for index in range(1, conf.Code.hist + 1):
            try:
                i = self.of.hist[-index]
            except IndexError:
                break
            if (here - i.address) > i.length:
                T.rows.insert(0, tokenrow([(Token.Literal, "|")]))
            if i.address < here:
                T.rows.insert(0, tokenrow(blockView.instr(i)))
                here = i.address
        # add info (symbols, marks) from task OS/state:
        T = self.of.task.view.code(T)
        # add header infos:
        if hasattr(self.of.task, "helper_code"):
            infos = self.of.task.helper_code()
            if "cs_base" in infos:
                base = infos["cs_base"]
                T.header = "[ code (cs_base: %s) ]" % base
        return T

    def frame_stack(self):
        table = vltable()
        table.header = "[ stack ]"
        flag_more = False
        sp = []
        for x in self.of.task.cpu.registers:
            if x.etype & regtype.STACK:
                v = self.of.task.state(x)
                sp.append(v)
        # size of stacks' elements:
        sz = self.of.pc.length
        if len(sp) == 0:
            logger.warning("stack pointer not found")
            return table
        delta = conf.Emu.stacksize
        # if we have more than 1 stack registers (like esp, ebp)
        # top of stack (esp) MUST appear *before* base (ebp)
        # we can adjust delta to show the full strack frame:
        if len(sp) == 2:
            base = sp[1]
            if base.etype & et_vrb and base._is_cst and base.value != 0:
                delta = base - sp[0]
                if delta._is_cst:
                    delta = delta.value
                if delta < 0:
                    logger.warning("empty stack")
                if delta > conf.Emu.stacksize:
                    flag_more = True
                    delta = conf.Emu.stacksize
        # if a stack helper is defined in the task object, we
        # let it possibly adjust sp expression, delta, sz, or add
        # some info in the output.
        if hasattr(self.of.task, "helper_stack"):
            sp, delta, sz, info = self.of.task.helper_stack(sp, delta)
            table.header = "[ stack (%s) ]" % info
        else:
            sp = sp[0]
        if not (sp._is_cst and sp.value == 0):
            table.rows = self.of.task.view.memory(sp, delta // sz, 1, sz * 8).rows
            if conf.Emu.stackdown:
                table.rows = table.rows[::-1]
            if conf.Emu.stackdown and flag_more:
                table.rows.insert(0, tokenrow([(Token.Literal, icons.dots)]))
            elif flag_more:
                table.addrow([(Token.Literal, icons.dots)])
        table.update()
        return table

    def frame_callstack(self):
        p = self.engine.RichTree(self.of.hist.callstack, "callstack")
        return p

    def __str__(self):
        t = []
        for f in self.frames:
            try:
                t.append(self.engine.highlighted(f()))
            except Exception as e:
                logger.warning("emulView.%s: %s" % (f.__name__, e))
        return "\n".join(t)


# -------------------------------------------------------------------------------


class archView(View):
    def __init__(self, of):
        super().__init__(of)

    def show_spec(self, s):
        mnemo = s.iattr.get("mnemonic", "?")
        specf = s.format
        return "{0:<16}: {1}".format(mnemo, specf)

    def show_subtree(self, root, wh=""):
        f, l = root
        if f == 0:  # leaves:
            t = [wh + icons.hor + self.show_spec(s) for s in l]
        else:
            t = []
            c = "%s%s[& %x ==" % (wh, icons.hor, f)
            wh += "  " + icons.ver
            for k, fl in l.items():
                t.append("%s %x]" % (c, k))
                t.extend(self.show_subtree(fl, wh))
        return t

    def __str__(self):
        t = []
        for root in self.of.specs:
            t.extend(self.show_subtree(root))
        return "\n".join(t)


# -------------------------------------------------------------------------------
