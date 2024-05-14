# -*- coding: utf-8 -*-

# This code is part of Amoco
# Copyright (C) 2024 Axel Tillequin (bdcht3@gmail.com)
# published under GPLv2 license
"""
cas/blobs.py
============

The blobs module implements all symbolic representations of structured
memory objects.

A blob is a meta-expression in the sense that it is
not a asm-level representation of data but rather a higher level (src)
representation of structured data. Hence, it would normally not be
present in any expression tree but can be present in a MemoryZone or
used by special instructions to operate on "blobs" of data like
rep movs, rep stos, or SSE stuff.
"""

from amoco.config import conf
from amoco.logger import Log

logger = Log(__name__)
logger.debug("loading module")
from amoco.ui import render
import operator

from amoco.system.structs import uint8,uint16,uint32,uint64
from amoco.cas.expressions import *

# ------------------------------------------------------------------------------
class blob(object):
    """the core class for blobs.

    A blob is an expression producer that can represent an array of
    fixed-size symbolic elements, a C-like structure with symbolic
    fields. The access to an element or field should produce the
    corresponding expression, either a cst or mem, or top.
    A blob exposes an exp API in order to be easily manipulated
    by current mapper and MemoryMap classes, however the size of the
    blob or its address are possibly symbolic (which in most cases
    will produce top expressions).
    """
    def __init__(self,dt,a=None,raw=None):
        self.dt = dt()
        self.a = a
        self.raw = raw
        self.variant = 0

    @property
    def etype(self):
        if self.raw is not None:
            bt = et_cst
        elif self.a and self.a._is_top:
            bt = -1
        else:
            bt = et_mem
        return bt|self.variant

    @property
    def size(self):
        return self.dt.size()*8

    @property
    def length(self):
        return len(self.dt)

    def __len__(self):
        return self.length

    def __unicode__(self):
        name = self.dt.__class__.__name__
        if conf.Cas.unicode:
            return u"\u27e6<%s>\u27e7"%name
        else:
            return "[<%s>]"%name

    def __str__(self):
        res = self.__unicode__()
        try:
            return str(res)
        except UnicodeEncodeError:
            return res.encode("utf-8")

    def toks(self, **kargs):
        tt = render.Token.Constant if self.a is None else render.Token.Memory
        return [(tt, "%s" % self)]

    def to_bytes(self,endian=1):
        return self.raw

    def bytes(self,sta,sto,endian=1):
        if self._is_cst:
            return self.raw[sta:sto]
        else:
            sz = (sto-sta)*8
            return mem(self.a,sz,disp=sta,endian=endian)

    def is_(self,t):
        return t & self.etype

    @property
    def _is_def(self):
        return self.etype > 0
    @property
    def _is_top(self):
        return self.etype < 0
    @property
    def _is_cst(self):
        return et_cst & self.etype
    @property
    def _is_reg(self):
        return et_reg & self.etype
    @property
    def _is_cmp(self):
        return et_cmp & self.etype
    @property
    def _is_slc(self):
        return et_slc & self.etype
    @property
    def _is_mem(self):
        return et_mem & self.etype
    @property
    def _is_ext(self):
        return et_ext & self.etype
    @property
    def _is_lab(self):
        return et_lab & self.etype
    @property
    def _is_ptr(self):
        return et_ptr & self.etype
    @property
    def _is_tst(self):
        return et_tst & self.etype
    @property
    def _is_eqn(self):
        return et_eqn & self.etype
    @property
    def _is_vec(self):
        return et_vec & self.etype

# ------------------------------------------------------------------------------

class blob_ptr(blob):
    def __init__(self,dt,a):
        if isinstance(dt,int):
            l = dt
            try:
                dt = [uint8,uint16,uint32,uint64][l>>1]
            except IndexError:
                logger.error("invalid blob element size: %d"%l)
                raise ValueError(l)
        super().__init__(dt,a)
        self.data = None

    @property
    def length(self):
        return self.dt.fields[0].size()

    def as_array(self,N,d=0):
        self.d = d
        if isinstance(N,exp):
            if N._is_cst:
                N = N.v # we want the value as unsigned
            else:
                logger.warning("symbolic blob_ptr array length !")
                N = float('Infinity')
        if N<0: N=-N
        self.dt.fields[0].count = N
        self.variant = et_vra
        return self

    def eval(self,env):
        blen = self.length
        if blen==float('Infinity') or (self.a is None):
            self.data = None
        else:
            self.a = env(self.a)
            env.mmap.restruct()
            if self.d==1:
                self.a.disp -= blen
            try:
                data = env.mmap.read(self.a,self.length)
            except Exception:
                logger.warning("memory address is not mapped")
            else:
                self.data = data
                # data is a list of expressions or raw bytes
                if len(data)==1:
                    v = data[0]
                    if isinstance(v,bytes):
                        # we make self a cst (self.etype is et_cst.)
                        self.raw = v
                        self.val = self.dt.unpack(v)
                else:
                    # data has symbolic part(s):
                    logger.warning("memory blob has symbolic values")
        return self

    def __getitem__(self,i):
        if self.d==1:
            N = self.length
            i = (N-i-1)%N
        bsz = self.dt.size()
        if self._is_cst:
            if isinstance(self.val,(tuple,list)):
                return cst(self.val[i],bsz*8)
        elif self._is_top:
            return top(bsz*8)
        return self.bytes(i*bsz,(i+1)*bsz)

# ------------------------------------------------------------------------------

class blob_comp(blob):
    def __init__(self,dt,el):
        if isinstance(dt,int):
            l = dt
            try:
                dt = [uint8,uint16,uint32,uint64][l>>1]
            except IndexError:
                logger.error("invalid blob element size: %d"%l)
                raise ValueError(l)
        super().__init__(dt,None)
        self.el = el
        if el._is_cst:
            self.raw = el.to_bytes()
            self.val = self.dt.unpack(self.raw)
            self.data = self.el

    @property
    def length(self):
        return self.dt.fields[0].size()

    @property
    def etype(self):
        if self.raw is not None:
            bt = et_cst
        elif self.el._is_top:
            bt = -1
        else:
            bt = et_cmp
        return bt|self.variant

    def as_array(self,N,d=0):
        self.d = d
        if isinstance(N,exp):
            if N._is_cst:
                N = N.v # we want the value as unsigned
            else:
                logger.warning("symbolic blob_comp array length !")
                N = float('Infinity')
        if N<0: N=-N
        self.dt.fields[0].count = N
        self.variant = et_vra
        if N<float('Infinity'):
            if self.el._is_cst:
                self.raw = self.raw*N
                self.val = self.dt.unpack(self.raw)
            try:
                self.data = composer([self.el]*N)
            except RecursionError:
                self.data = None
        return self

    def eval(self,env):
        return self

    def bytes(self,sta,sto,endian=1):
        if self._is_cst:
            return self.raw[sta:sto]
        elif self.length<float('inf') and self.data is not None:
            return self.data.bytes(sta,sto,endian)
        else:
            sz = self.dt.size()
            l = (sto-sta)
            n = l//sz
            o = sta%sz
            return blob_comp(self.dt,self.el).as_array(n+2).bytes(o,o+l,endian)
