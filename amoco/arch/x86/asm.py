# -*- coding: utf-8 -*-

# This code is part of Amoco
# Copyright (C) 2006-2011 Axel Tillequin (bdcht3@gmail.com)
# published under GPLv2 license

# ruff: noqa: F405
from .env import *  # noqa: F403
from amoco.arch.x86 import hw
from amoco.cas.utils import AddWithCarry, SubWithBorrow

from amoco.logger import Log

logger = Log(__name__)
logger.debug("loading module")


# ------------------------------------------------------------------------------
# utils :
def push(fmap, x):
    fmap[esp] = fmap(esp - x.length)
    fmap[mem(esp, x.size, seg=ss)] = x


def pop(fmap, l, sz=0):
    v = fmap(mem(esp, l.size, seg=ss))
    nb = (sz // 8) or l.length
    fmap[esp] = fmap(esp + nb)
    fmap[l] = v


def parity(x):
    x = x ^ (x >> 1)
    x = (x ^ (x >> 2)) & 0x11111111
    x = x * 0x11111111
    p = (x >> 28).bit(0)
    return p


def parity8(x):
    y = x ^ (x >> 4)
    y = cst(0x6996, 16) >> (y[0:4])
    p = y.bit(0)
    return p


def halfcarry(x, y, c=None):
    s, carry, o = AddWithCarry(x[0:4], y[0:4], c)
    return carry


def halfborrow(x, y, c=None):
    s, carry, o = SubWithBorrow(x[0:4], y[0:4], c)
    return carry


# ------------------------------------------------------------------------------
def i_AAA(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    alv = fmap(al)
    cond = (alv & 0xF > 9) | fmap(af)
    fmap[al] = tst(cond, (alv + 6) & 0xF, alv & 0xF)
    fmap[ah] = tst(cond, fmap(ah) + 1, fmap(ah))
    fmap[af] = cond
    fmap[cf] = cond


def i_DAA(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    alv = fmap(al)
    cfv = fmap(cf)
    cond = (alv & 0xF > 9) | fmap(af)
    _r, carry, overflow = AddWithCarry(alv, cst(6, 8))
    fmap[al] = tst(cond, _r, alv)
    fmap[cf] = tst(cond, carry | cfv, cfv)
    fmap[af] = cond
    cond = (alv > 0x99) | cfv
    alv = fmap(al)
    fmap[al] = tst(cond, alv + 0x60, alv)
    fmap[cf] = cond


def i_AAS(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    alv = fmap(al)
    cond = (alv & 0xF > 9) | fmap(af)
    fmap[ax] = tst(cond, fmap(ax) - 6, fmap(ax))
    fmap[ah] = tst(cond, fmap(ah) - 1, fmap(ah))
    fmap[af] = cond
    fmap[cf] = cond
    fmap[al] = tst(cond, fmap(al) & 0xF, alv & 0xF)


def i_DAS(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    alv = fmap(al)
    cfv = fmap(cf)
    cond = (alv & 0xF > 9) | fmap(af)
    _r, carry, overflow = SubWithBorrow(alv, cst(6, 8))
    fmap[al] = tst(cond, _r, alv)
    fmap[cf] = tst(cond, carry | cfv, cfv)
    fmap[af] = cond
    cond = (alv > 0x99) | cfv
    alv = fmap(al)
    fmap[al] = tst(cond, alv - 0x60, alv)
    fmap[cf] = cond


def i_AAD(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    imm8 = i.operands[0]
    _al = fmap(al)
    _ah = fmap(ah)
    _r = _al + (_ah * imm8)
    fmap[al] = _r
    fmap[ah] = cst(0, 8)
    fmap[zf] = _r == 0
    fmap[sf] = _r < 0


def i_AAM(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    imm8 = i.operands[0]
    _al = fmap(al)
    fmap[ah] = _al / imm8
    _r = _al & (imm8 - 1)
    fmap[al] = _r
    fmap[zf] = _r == 0
    fmap[sf] = _r < 0


def i_XLATB(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    _table = bx if i.misc["opdsz"] == 16 else ebx
    fmap[al] = fmap(mem(_table + al.zeroextend(_table.size), 8, seg=ds))


# ------------------------------------------------------------------------------
def i_BSWAP(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    dst = i.operands[0]
    _t = fmap(dst)
    fmap[dst[0:8]] = _t[24:32]
    fmap[dst[8:16]] = _t[16:24]
    fmap[dst[16:24]] = _t[8:16]
    fmap[dst[24:32]] = _t[0:8]


def i_NOP(i, fmap):
    fmap[eip] = fmap[eip] + i.length


def i_WAIT(i, fmap):
    fmap[eip] = fmap[eip] + i.length


def i_MWAIT(i, fmap):
    fmap[eip] = fmap[eip] + i.length


def i_ENTER(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    AllocSize = i.operands[0].v  # required size in bytes (imm16)
    NestingLevel = i.operands[1].v % 32
    opdsz = i.misc["opdsz"] or internals["mode"]
    _bp = ebp if opdsz == 32 else bp
    _sp = esp if opdsz == 32 else sp
    push(fmap, fmap(_bp))
    frame = fmap(_sp)
    if NestingLevel > 1:
        for _ in range(NestingLevel):
            fmap[_bp] = fmap(_bp) - _bp.length
            push(fmap, fmap(_bp))
    if NestingLevel > 0:
        push(fmap, frame)
    fmap[_bp] = frame
    fmap[esp] = fmap(esp - AllocSize)


# LEAVE instruction is a shortcut for 'mov esp,ebp ; pop ebp ;'
def i_LEAVE(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    fmap[esp] = fmap(ebp)
    pop(fmap, ebp)


def i_RET(i, fmap):
    opdsz = i.misc["opdsz"] or internals["mode"]
    _ip = eip if opdsz == 32 else ip
    if len(i.operands) > 0:
        src = i.operands[0].v
        pop(fmap, _ip)
        fmap[esp] = fmap(esp) + src
    else:
        pop(fmap, _ip)


def i_HLT(i, fmap):
    fmap[eip] = top(32)


# ------------------------------------------------------------------------------


def _ins_(i, fmap, l):
    adrsz = i.misc["adrsz"] or internals["mode"]
    counter = ecx if adrsz == 32 else cx
    dst_r = edi if adrsz == 32 else di
    dst = fmap(ptr(dst_r, seg=es))
    cnt = 1
    if i.misc["rep"]:
        cnt = fmap(counter)
        if cnt == 0:
            return
        fmap[counter] = cst(0, counter.size)
    src = hw.IO.get_port(fmap(dx)).In(env=fmap, dl=l)
    fmap[dst] = src
    off = cnt * l
    fmap[dst_r] = tst(fmap(df), fmap(dst_r) - off, fmap(dst_r) + off)
    fmap[eip] = fmap[eip] + i.length


def i_INSB(i, fmap):
    _ins_(i, fmap, 1)


def i_INSW(i, fmap):
    _ins_(i, fmap, 2)


def i_INSD(i, fmap):
    _ins_(i, fmap, 4)


# ------------------------------------------------------------------------------
from amoco.cas.blobs import blob_ptr, blob_comp


def _outs_(i, fmap, l):
    adrsz = i.misc["adrsz"] or internals["mode"]
    counter = ecx if adrsz == 32 else cx
    src_r = esi if adrsz == 32 else si
    src_seg = i.misc["segreg"]
    if src_seg is None:
        src_seg = ds
    cnt = 1
    if i.misc["rep"]:
        cnt = fmap(counter)
        if cnt == 0:
            return
        fmap[counter] = cst(0, counter.size)
    src = ptr(src_r, seg=src_seg)
    direction = fmap(df)
    data = blob_ptr(dl=l, a=src).as_array(N=cnt, d=direction)
    off = cnt * l
    hw.IO.get_port(fmap(dx)).Out(env=fmap, src=fmap(data))
    fmap[src_r] = tst(fmap(df), fmap(src_r) - off, fmap(src_r) + off)
    fmap[eip] = fmap[eip] + i.length


def i_OUTSB(i, fmap):
    _outs_(i, fmap, 1)


def i_OUTSW(i, fmap):
    _outs_(i, fmap, 2)


def i_OUTSD(i, fmap):
    _outs_(i, fmap, 4)


# ------------------------------------------------------------------------------
def i_INT3(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    do_interrupt_call(i, fmap, cst(3, 8))


def i_CLC(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    fmap[cf] = bit0


def i_STC(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    fmap[cf] = bit1


def i_CLD(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    fmap[df] = bit0


def i_STD(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    fmap[df] = bit1


def i_CMC(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    fmap[cf] = ~fmap(cf)


def i_CBW(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    fmap[ax] = fmap(al).signextend(16)


def i_CWDE(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    fmap[eax] = fmap(ax).signextend(32)


def i_CWD(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    x = fmap(ax).signextend(32)
    fmap[dx] = x[16:32]
    fmap[ax] = x[0:16]


def i_CDQ(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    x = fmap(eax).signextend(64)
    fmap[edx] = x[32:64]
    fmap[eax] = x[0:32]


def i_PUSHAD(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    tmp = fmap(esp)
    push(fmap, fmap(eax))
    push(fmap, fmap(ecx))
    push(fmap, fmap(edx))
    push(fmap, fmap(ebx))
    push(fmap, tmp)
    push(fmap, fmap(ebp))
    push(fmap, fmap(esi))
    push(fmap, fmap(edi))


def i_POPAD(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    pop(fmap, edi)
    pop(fmap, esi)
    pop(fmap, ebp)
    fmap[esp] = fmap[esp] + 4
    pop(fmap, ebx)
    pop(fmap, edx)
    pop(fmap, ecx)
    pop(fmap, eax)


def i_PUSHFD(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    push(fmap, fmap(eflags) & 0x00FCFFFF)


def i_POPFD(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    pop(fmap, eflags)


def i_LAHF(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    x = fmap(composer([cf, bit1, pf, bit0, af, bit0, zf, sf]))
    fmap[ah] = x


def i_SAHF(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    fmap[eflags[0:8]] = fmap(ah)
    fmap[eflags[1:2]] = bit1
    fmap[eflags[3:4]] = bit0
    fmap[eflags[5:6]] = bit0


# ------------------------------------------------------------------------------
def _cmps_(i, fmap, l):
    counter = cx if i.misc["adrsz"] else ecx
    dst = fmap(mem(edi, l * 8, seg=es))
    src_seg = i.misc["segreg"]
    if src_seg is None:
        src_seg = ds
    src = fmap(mem(esi, l * 8, seg=src_seg))
    x, carry, overflow = SubWithBorrow(dst, src)
    if i.misc["rep"] or i.misc["repne"]:
        zv = bit0 if i.misc["rep"] else bit1
        cnt = fmap(counter)
        cond = (cnt == 0) | (fmap(zf) == zv)
        if cond == bit1:
            fmap[eip] = fmap[eip] + i.length
            return
        elif cond == bit0:
            fmap[counter] = cnt - 1
        else:
            fmap[counter] = cst(0, counter.size)
            fmap[edi] = top(32)
            fmap[esi] = top(32)
            return
    else:
        fmap[eip] = fmap[eip] + i.length
    fmap[af] = halfborrow(dst, src)
    fmap[pf] = parity8(x[0:8])
    fmap[zf] = x == 0
    fmap[sf] = x < 0
    fmap[cf] = carry
    fmap[of] = overflow
    fmap[edi] = tst(fmap(df), fmap(edi) - l, fmap(edi) + l)
    fmap[esi] = tst(fmap(df), fmap(esi) - l, fmap(esi) + l)


def i_CMPSB(i, fmap):
    _cmps_(i, fmap, 1)


def i_CMPSW(i, fmap):
    _cmps_(i, fmap, 2)


def i_CMPSD(i, fmap):
    if i.misc["opdsz"] == 128:
        return
    else:
        _cmps_(i, fmap, 4)


# ------------------------------------------------------------------------------
def _scas_(i, fmap, l):
    adrsz = i.misc["adrsz"] or internals["mode"]
    counter = ecx if adrsz == 32 else cx
    dst_r = edi if adrsz == 32 else di
    a = fmap({1: al, 2: ax, 4: eax}[l])
    src = fmap(mem(edi, l * 8, seg=es))
    x, carry, overflow = SubWithBorrow(a, src)
    if i.misc["rep"] or i.misc["repne"]:
        zv = bit0 if i.misc["rep"] else bit1
        cnt = fmap(counter)
        cond = (cnt == 0) | (fmap(zf) == zv)
        if cond == bit1:
            fmap[eip] = fmap[eip] + i.length
            return
        elif cond == bit0:
            fmap[counter] = cnt - 1
        else:
            fmap[counter] = cst(0, counter.size)
            fmap[dst_r] = top(dst_r.size)
            return
    else:
        fmap[eip] = fmap[eip] + i.length
    fmap[af] = halfborrow(a, src)
    fmap[pf] = parity8(x[0:8])
    fmap[zf] = x == 0
    fmap[sf] = x < 0
    fmap[cf] = carry
    fmap[of] = overflow
    fmap[dst_r] = tst(fmap(df), fmap(dst_r) - l, fmap(dst_r) + l)


def i_SCASB(i, fmap):
    _scas_(i, fmap, 1)


def i_SCASW(i, fmap):
    _scas_(i, fmap, 2)


def i_SCASD(i, fmap):
    _scas_(i, fmap, 4)


# ------------------------------------------------------------------------------


def _lods_(i, fmap, l):
    adrsz = i.misc["adrsz"] or internals["mode"]
    counter = ecx if adrsz == 32 else cx
    src_r = esi if adrsz == 32 else si
    dst = {1: al, 2: ax, 4: eax}[l]
    src_seg = i.misc["segreg"]
    if src_seg is None:
        src_seg = ds
    src = ptr(esi, seg=src_seg)
    direction = fmap(df)
    cnt = 1
    if i.misc["rep"]:
        cnt = fmap(counter)
        fmap[counter] = cst(0, counter.size)
    data = fmap(blob_ptr(dt=l, a=src).as_array(cnt, direction))
    fmap[dst] = data[-1]
    off = cnt * l
    fmap[src_r] = tst(direction, fmap(src_r) - off, fmap(src_r) + off)
    fmap[eip] = fmap[eip] + i.length


def i_LODSB(i, fmap):
    _lods_(i, fmap, 1)


def i_LODSW(i, fmap):
    _lods_(i, fmap, 2)


def i_LODSD(i, fmap):
    _lods_(i, fmap, 4)


# ------------------------------------------------------------------------------


def _stos_(i, fmap, l):
    adrsz = i.misc["adrsz"] or internals["mode"]
    counter = ecx if adrsz == 32 else cx
    dst_r = edi if adrsz == 32 else di
    src = fmap({1: al, 2: ax, 4: eax}[l])
    dst = fmap(ptr(edi, seg=es))
    direction = fmap(df)
    cnt = 1
    fmap[eip] = fmap[eip] + i.length
    if i.misc["rep"]:
        cnt = fmap(counter)
        if cnt == 0:
            return
        fmap[counter] = cst(0, counter.size)
    src = blob_comp(dt=l, el=src).as_array(cnt, direction)
    fmap[dst] = src
    off = cnt * l
    fmap[dst_r] = tst(direction, fmap(dst_r) - off, fmap(dst_r) + off)


def i_STOSB(i, fmap):
    _stos_(i, fmap, 1)


def i_STOSW(i, fmap):
    _stos_(i, fmap, 2)


def i_STOSD(i, fmap):
    _stos_(i, fmap, 4)


# ------------------------------------------------------------------------------


def _movs_(i, fmap, l):
    adrsz = i.misc["adrsz"] or internals["mode"]
    counter = ecx if adrsz == 32 else cx
    dst_r = edi if adrsz == 32 else di
    src_r = esi if adrsz == 32 else si
    dst = fmap(ptr(dst_r, seg=es))
    src_seg = i.misc["segreg"]
    if src_seg is None:
        src_seg = ds
    src = ptr(src_r, seg=src_seg)
    direction = fmap(df)
    cnt = 1
    fmap[eip] = fmap[eip] + i.length
    if i.misc["rep"]:
        cnt = fmap(counter)
        if cnt == 0:
            return
        fmap[counter] = cst(0, counter.size)
    src = blob_ptr(dt=l, a=src)
    fmap[dst] = fmap(src.as_array(N=cnt, d=direction))
    off = cnt * l
    src_v = fmap(src_r)
    dst_v = fmap(dst_r)
    fmap[src_r] = tst(direction, src_v - off, src_v + off)
    fmap[dst_r] = tst(direction, dst_v - off, dst_v + off)


def i_MOVSB(i, fmap):
    _movs_(i, fmap, 1)


def i_MOVSW(i, fmap):
    _movs_(i, fmap, 2)


def i_MOVSD(i, fmap):
    if i.misc["opdsz"] == 128:
        sse_MOVSD(i, fmap)
    else:
        _movs_(i, fmap, 4)


# ------------------------------------------------------------------------------
def i_IN(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    op1 = i.operands[0]
    op2 = fmap(i.operands[1])
    data = hw.IO.get_port(op2).In(env=fmap, dl=op1.length)
    fmap[op1] = data


def i_OUT(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    op1 = fmap(i.operands[0])
    op2 = fmap(i.operands[1])
    hw.IO.get_port(op1).Out(env=fmap, src=op2)


# op1_src retreives fmap[op1] (op1 value):
def i_PUSH(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    op1 = fmap(i.operands[0])
    opdsz = i.misc["opdsz"] or internals["mode"]
    if op1.size == 8:
        op1 = op1.signextend(opdsz)  # push imm8
    elif op1.size == 16:
        op1 = op1.zeroextend(opdsz)  # push segm register
    push(fmap, op1)


# op1_dst retreives op1 location:
def i_POP(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    op1 = i.operands[0]
    opdsz = i.misc["opdsz"] or internals["mode"]
    pop(fmap, op1, sz=opdsz)


def i_CALL(i, fmap):
    opdsz = i.misc["opdsz"] or internals["mode"]
    _ip = eip if opdsz == 32 else ip
    pc = fmap(_ip) + i.length
    fmap[_ip] = pc
    push(fmap, pc)
    op1 = fmap(i.operands[0])
    op1 = op1.signextend(pc.size)
    target = pc + op1 if not i.misc["absolute"] else op1
    fmap[_ip] = target


def i_CALLF(i, fmap):
    opdsz = i.misc["opdsz"] or internals["mode"]
    _ip = eip if opdsz == 32 else ip
    pc = fmap(_ip) + i.length
    fmap[_ip] = pc
    push(fmap, fmap(cs).zeroextend(opdsz))
    push(fmap, pc)
    do_far_jump(i, fmap, reason="CALLF")


def i_JMP(i, fmap):
    pc = fmap[eip] + i.length
    fmap[eip] = pc
    op1 = fmap(i.operands[0])
    op1 = op1.signextend(pc.size)
    target = pc + op1 if not i.misc["absolute"] else op1
    if internals["mode"] == 16 and not i.misc["opdsz"]:
        target = target & 0xFFFF
    fmap[eip] = target


def i_JMPF(i, fmap):
    pc = fmap[eip] + i.length
    fmap[eip] = pc
    do_far_jump(i, fmap)


def do_far_jump(i, fmap, reason="JMPF"):
    op1 = i.operands[0]
    if internals["mode"] == 16:
        if op1._is_ptr:
            selector = op1.seg
            offset = op1.base
        elif op1._is_mem:
            desc = fmap(op1)
            sz = 32 if i.misc["opdsz"] else 16
            offset = desc[0:sz]
            selector = desc[sz : desc.size]
    else:
        sz = 16 if i.misc["opdsz"] else 32
        if op1._is_ptr:
            selector = op1.seg
            offset = op1.base
        elif op1._is_mem:
            fa = fmap(op1)
            selector = fa[sz : fa.size]
            offset = fa[0:sz]
    if fmap(PE) == bit0:
        # still in (un)real mode:
        fmap[cs] = selector
        fmap[eip] = offset.zeroextend(32)
        return
    # read cs descriptor from GDT or LDT
    _e = read_descriptor(fmap, selector)
    if _e is None:
        logger.error(reason)
        fmap[eip] = top(32)
        return
    # and update mode, hidden parts (MSRs) and eip:
    if _e.s == DESC_SEGMENT:
        fmap[cs] = selector
        load_segment(fmap, cs, _e)
        target = offset.zeroextend(32)
        fmap[eip] = target
        return
    else:
        if _e.type == GATE_TASK:
            tss_sel = cst(_e.base0, 16)
            _e = read_descriptor(fmap, tss_sel)
            selector = tss_sel
        if _e.type == DESC_TSS32_OK and fmap(PE) == bit1:
            switch_tss32(fmap, _e, selector, reason)
            return
        if _e.type == GATE_CALL32:
            _g = call_gate_t(_e.pack())
            fmap[cs] = cst(_g.selector, 16)
            _e = read_descriptor(fmap, fmap(cs))
            if _e.type == DESC_SEGMENT:
                load_segment(fmap, cs, _e)
                fmap[eip] = _g.offset()
                return
    logger.warning("%s to unsupported descriptor", reason)


def read_descriptor(fmap, selector):
    if isinstance(selector, int):
        selector = cst(selector, 16)
    _ti = selector[2:3]
    offset = selector[3:16].zeroextend(32) * 8
    if _ti == bit0:
        Tmx = GDTR[0:16]  # noqa: F841
        Tbl = GDTR[16:48]
    elif _ti == bit1:
        Tmx = seglimit(LDTR)  # noqa: F841
        Tbl = segbase(LDTR)
    adr = Tbl + offset
    desc = fmap(mem(adr, 64))
    if desc._is_cst:
        _e = gdt_entry_t(desc.to_bytes())
        return _e
    logger.verbose("impossible to access descriptor " % desc)
    return None


def write_descriptor(fmap, selector, new_desc):
    if isinstance(selector, int):
        selector = cst(selector, 16)
    if isinstance(new_desc, bytes):
        new_desc = gdt_entry_t(new_desc)
    _ti = selector[2:3]
    offset = selector[3:16].zeroextend(32) * 8
    if _ti == bit0:
        Tmx = GDTR[0:16]
        Tbl = GDTR[16:48]
    elif _ti == bit1:
        Tmx = seglimit(LDTR)  # noqa: F841
        Tbl = segbase(LDTR)
    # Tbl holds a virtual address if PG is 1
    # since we use _Mem_write, we must first translate
    # it to its physical address:
    adr = ptr(fmap(Tbl) + offset).eval(fmap)
    fmap._Mem_write(adr, new_desc.pack())


def load_segment(fmap, seg, desc):
    rpl = fmap(seg)[0:2]
    if desc is not None:
        dpl = desc.dpl
        if rpl._is_cst and dpl <= (rpl.v):
            fmap[segbase(seg)] = cst(desc.base(), 32)
            if seg == cs:
                internals["mode"] = 32 if desc.d else 16
                internals["ring"] = dpl
        else:
            logger.error("load_segment privilege error")
            fmap[segbase(seg)] = top(32)
    else:
        logger.warning("load_segment into %s: invalid descriptor" % seg)


def switch_tss32(fmap, e, selector, reason):
    # qemu reads the new tss before saving the current one...
    # (see tcg/seg_helper.c:switch_tss_ra).
    # not sure why its done this way, may be saving the current
    # could erase the new one ?? anyway lets do it the same way.
    new_tss = read_tss32(fmap, e)
    save_tss32(fmap, reason)
    if reason in ("JMPF", "CALLF"):
        # set BUSY flag in descriptor:
        e._v.type |= 2
        write_descriptor(fmap, selector, e)
    if reason == "CALLF":
        # new task is "nested" so it needs to remember link to current:
        adr = cst(e.base(), 32)
        fmap[mem(adr, 32, disp=new_tss.offset_of("link"))] = fmap(TR)
    # now change state to new TR & TSS:
    fmap[TR] = selector
    load_segment(fmap, TR, e)
    load_tss32(fmap, new_tss, reason)


def read_tss32(fmap, e):
    adr = cst(e.base(), 32)
    sz = tss32_entry_t.size()
    if sz > e.limit() + 1:
        logger.error("tss segment too short @ %s" % adr)
    tss_ = fmap(mem(adr, sz * 8))
    if tss_._is_cst:
        return tss32_entry_t(tss_.to_bytes())
    return tss_


def save_tss32(fmap, reason):
    old_tss = tss32_entry_t()
    cur_tr = read_descriptor(fmap, fmap(TR))
    if reason in ("JMPF", "IRET"):
        # clear BUSY flag for current tss descriptor:
        cur_tr._v.type &= ~2
        write_descriptor(fmap, fmap(TR), cur_tr)
    old_eflags = fmap(eflags)
    if reason == "IRET":
        # clear nested flag since the interrupt task is now terminated
        NT_MASK = 0x00004000
        old_eflags &= ~NT_MASK
    fmap[mem(segbase(TR), 32, disp=old_tss.offset_of("EIP"))] = fmap(eip)
    fmap[mem(segbase(TR), 32, disp=old_tss.offset_of("EFLAGS"))] = old_eflags
    fmap[mem(segbase(TR), 32, disp=old_tss.offset_of("EAX"))] = fmap(eax)
    fmap[mem(segbase(TR), 32, disp=old_tss.offset_of("ECX"))] = fmap(ecx)
    fmap[mem(segbase(TR), 32, disp=old_tss.offset_of("EDX"))] = fmap(edx)
    fmap[mem(segbase(TR), 32, disp=old_tss.offset_of("EBX"))] = fmap(ebx)
    fmap[mem(segbase(TR), 32, disp=old_tss.offset_of("ESP"))] = fmap(esp)
    fmap[mem(segbase(TR), 32, disp=old_tss.offset_of("EBP"))] = fmap(ebp)
    fmap[mem(segbase(TR), 32, disp=old_tss.offset_of("ESI"))] = fmap(esi)
    fmap[mem(segbase(TR), 32, disp=old_tss.offset_of("EDI"))] = fmap(edi)
    fmap[mem(segbase(TR), 16, disp=old_tss.offset_of("ES"))] = fmap(es)
    fmap[mem(segbase(TR), 16, disp=old_tss.offset_of("CS"))] = fmap(cs)
    fmap[mem(segbase(TR), 16, disp=old_tss.offset_of("SS"))] = fmap(ss)
    fmap[mem(segbase(TR), 16, disp=old_tss.offset_of("DS"))] = fmap(ds)
    fmap[mem(segbase(TR), 16, disp=old_tss.offset_of("FS"))] = fmap(fs)
    fmap[mem(segbase(TR), 16, disp=old_tss.offset_of("GS"))] = fmap(gs)


def load_tss32(fmap, tss_, reason):
    fmap[TS] = bit1
    try:
        if isinstance(tss_, tss32_entry_t):
            fmap[cr3] = cst(tss_.CR3, 32)
            mmu_cache.clear()
            fmap[eip] = cst(tss_.EIP, 32)
            fmap[eax] = cst(tss_.EAX, 32)
            fmap[ecx] = cst(tss_.ECX, 32)
            fmap[edx] = cst(tss_.EDX, 32)
            fmap[ebx] = cst(tss_.EBX, 32)
            fmap[esp] = cst(tss_.ESP, 32)
            fmap[ebp] = cst(tss_.EBP, 32)
            fmap[esi] = cst(tss_.ESI, 32)
            fmap[edi] = cst(tss_.EDI, 32)
            # update segment regs:
            fmap[es] = cst(tss_.ES, 16)
            fmap[cs] = cst(tss_.CS, 16)
            fmap[ss] = cst(tss_.SS, 16)
            fmap[ds] = cst(tss_.DS, 16)
            fmap[fs] = cst(tss_.FS, 16)
            fmap[gs] = cst(tss_.GS, 16)
            fmap[eflags] = cst(tss_.EFLAGS, 32)
            if reason == "CALLF":
                fmap[Nt] = bit1
            # update LDTR:
            if ldt_s := tss_.LDTR & (~7):
                fmap[LDTR] = cst(tss_.LDTR, 16)
                # read LDT descriptor in the GDT and update hidden parts:
                e = read_descriptor(fmap, ldt_s)
                if e is not None and e.type == DESC_LDT:
                    fmap[seglimit(LDTR)] = cst(e.limit(), 16)
                    fmap[segbase(LDTR)] = cst(e.base(), 32)
            for seg in (es, cs, ss, ds, fs, gs):
                desc = read_descriptor(fmap, fmap(seg))
                load_segment(fmap, seg, desc)
        elif isinstance(tss_, mem):
            logger.verbose("can't find TSS segment")
            raise NotImplementedError
    except Exception:
        fmap[eip] = top(32)
        logger.verbose("error in TSS switch:\n")
        logger.verbose("%s" % tss_)


def i_RETF(i, fmap):
    opdsz = i.misc["opdsz"] or internals["mode"]
    _ip = eip if opdsz == 32 else ip
    if len(i.operands) > 0:
        src = i.operands[0].v
        pop(fmap, _ip)
        pop(fmap, cs, sz=opdsz)
        fmap[esp] = fmap(esp) + src
    else:
        pop(fmap, _ip)
        pop(fmap, cs, sz=opdsz)
    desc = read_descriptor(fmap, fmap(cs))
    load_segment(fmap, cs, desc)


# ------------------------------------------------------------------------------
def _loop_(i, fmap, cond):
    pc = fmap[eip] + i.length
    opdsz = 16 if i.misc["opdsz"] else 32
    src = i.operands[0].signextend(32)
    loc = pc + src
    loc = loc[0:opdsz].zeroextend(32)
    counter = cx if i.misc["adrsz"] else ecx
    fmap[counter] = fmap(counter) - 1
    fmap[eip] = tst(fmap(cond), loc, pc)


def i_LOOP(i, fmap):
    counter = cx if i.misc["adrsz"] else ecx
    cond = counter != 0
    _loop_(i, fmap, cond)


def i_LOOPE(i, fmap):
    counter = cx if i.misc["adrsz"] else ecx
    cond = zf & (counter != 0)
    _loop_(i, fmap, cond)


def i_LOOPNE(i, fmap):
    counter = cx if i.misc["adrsz"] else ecx
    cond = (~zf) & (counter != 0)
    _loop_(i, fmap, cond)


# ------------------------------------------------------------------------------
def i_LSL(i, fmap):
    logger.verbose("%s semantic is not defined" % i.mnemonic)
    fmap[eip] = fmap[eip] + i.length


def i_LTR(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    selector = fmap(i.operands[0])
    fmap[TR] = selector
    _e = read_descriptor(fmap, selector)
    load_segment(fmap, TR, _e)
    if _e is None:
        logger.verbose("error in task register descriptor")
    # now load the information associated to this selector in the GDT


#######################


def i_Jcc(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    op1 = fmap(i.operands[0])
    op1 = op1.signextend(eip.size)
    cond = i.cond[1]
    fmap[eip] = tst(fmap(cond), fmap[eip] + op1, fmap[eip])


def i_JECXZ(i, fmap):
    pc = fmap[eip] + i.length
    fmap[eip] = pc
    op1 = fmap(i.operands[0])
    op1 = op1.signextend(pc.size)
    cond = ecx == 0
    target = tst(fmap(cond), fmap[eip] + op1, fmap[eip])
    fmap[eip] = target


def i_JCXZ(i, fmap):
    pc = fmap[eip] + i.length
    fmap[eip] = pc
    op1 = fmap(i.operands[0])
    op1 = op1.signextend(pc.size)
    cond = cx == 0
    target = tst(fmap(cond), fmap[eip] + op1, fmap[eip])
    fmap[eip] = target


def i_INT(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    op1 = i.operands[0]
    do_interrupt_call(i, fmap, op1)


def do_interrupt_call(i, fmap, op1):
    if isinstance(op1, int):
        op1 = cst(op1, 8)
        op1.sf = False
    vector = op1.v
    Tmx = fmap(IDTR[0:16])  # noqa: F841
    Tbl = fmap(IDTR[16:48])
    if internals["mode"] == 16:
        offset = vector << 2
        adr = Tbl + offset
        push(fmap, fmap(eflags[0:16]))
        fmap[If] = bit0
        fmap[tf] = bit0
        push(fmap, fmap(cs))
        push(fmap, fmap(ip))
        desc = fmap(mem(adr, 32))
        fmap[cs] = desc[16:32]
        fmap[eip] = desc[0:16].zeroextend(32)
        return
    # 32-bit protected-mode:
    offset = vector << 3
    adr = Tbl + offset
    desc = fmap(mem(adr, 64))
    if desc._is_cst:
        _e = idt_entry_t(desc.to_bytes())
    else:
        logger.error("INT %d" % vector)
        fmap[eip] = top(32)
        return
    if _e.type == GATE_TASK:
        tss_sel = cst(_e.selector, 16)
        # read TSS in GDT:
        _e = read_descriptor(fmap, tss_sel)
        if _e.type == DESC_TSS32_OK and fmap(PE) == bit1:
            # switch task with nesting (aka like a far call):
            # (nesting means that the TSS.link is updated with previous TR)
            switch_tss32(fmap, _e, tss_sel, "CALLF")
            return
        logger.error("interrupt task gate error (not a TSS?)")
    elif _e.type in (GATE_INTERRUPT32, GATE_TRAP32):
        # trap or interrupt 32-bit gates:
        if _e.type == GATE_INTERRUPT32:
            fmap[If] = bit0
        fmap[tf] = bit0
        fmap[Nt] = bit0
        selector = cst(_e.selector, 16)
        desc = read_descriptor(fmap, selector)
        if desc is not None and desc.s == DESC_SEGMENT:
            if desc.dpl < internals["ring"]:
                # inter-privilege-level-interrupt:
                logger.warning(
                    "inter-privilege-level-interrupt is not implemented yet..."
                )
            else:
                # intra-privilege-level-interrupt:
                push(fmap, fmap(eflags))
                push(fmap, fmap(cs).zeroextend(32))
                push(fmap, fmap(eip))
                fmap[cs] = selector
                load_segment(fmap, cs, desc)
                fmap[eip] = desc.offset()
            return
    logger.error("INT %d runtime error", vector)


def i_IRET(i, fmap):
    if internals["mode"] == 16 or not (fmap(Nt) == bit1):
        i_RETF(i, fmap)
    pop(fmap, eip)
    pop(fmap, cs, sz=32)
    pop(fmap, eflags)


def i_IRETD(i, fmap):
    if internals["mode"] == 16 or not (fmap(Nt) == bit1):
        i_RETF(i, fmap)
    pop(fmap, eip)
    pop(fmap, cs, sz=32)
    pop(fmap, eflags)


def i_INC(i, fmap):
    op1 = i.operands[0]
    fmap[eip] = fmap[eip] + i.length
    a = fmap(op1)
    b = cst(1, a.size)
    x, carry, overflow = AddWithCarry(a, b)
    # cf not affected
    fmap[af] = halfcarry(a, b)
    fmap[pf] = parity8(x[0:8])
    fmap[zf] = x == 0
    fmap[sf] = x < 0
    fmap[of] = overflow
    fmap[op1] = x


def i_DEC(i, fmap):
    op1 = i.operands[0]
    fmap[eip] = fmap[eip] + i.length
    a = fmap(op1)
    b = cst(1, a.size)
    x, carry, overflow = SubWithBorrow(a, b)
    # cf not affected
    fmap[af] = halfborrow(a, b)
    fmap[pf] = parity8(x[0:8])
    fmap[zf] = x == 0
    fmap[sf] = x < 0
    fmap[of] = overflow
    fmap[op1] = x


def i_NEG(i, fmap):
    op1 = i.operands[0]
    fmap[eip] = fmap[eip] + i.length
    a = cst(0, op1.size)
    b = fmap(op1)
    x, carry, overflow = SubWithBorrow(a, b)
    fmap[af] = halfborrow(a, b)
    fmap[pf] = parity8(x[0:8])
    fmap[cf] = b != 0
    fmap[zf] = x == 0
    fmap[sf] = x < 0
    fmap[of] = overflow
    fmap[op1] = x


def i_NOT(i, fmap):
    op1 = i.operands[0]
    fmap[eip] = fmap[eip] + i.length
    fmap[op1] = ~fmap(op1)


def i_SETcc(i, fmap):
    op1 = i.operands[0]
    fmap[eip] = fmap[eip] + i.length
    fmap[op1] = tst(fmap(i.cond[1]), cst(1, op1.size), cst(0, op1.size))


def i_MOV(i, fmap):
    op1 = i.operands[0]
    op2 = fmap(i.operands[1])
    fmap[eip] = fmap[eip] + i.length
    fmap[op1] = op2
    if fmap(PE) == bit1 and (op1 in (cs, ds, es, ss, fs, gs)):
        desc = read_descriptor(fmap, fmap(op1))
        load_segment(fmap, op1, desc)
    if op1 in (cr0, cr3):
        mmu_cache.clear()


def i_MOVBE(i, fmap):
    dst = i.operands[0]
    _t = fmap(i.operands[1])
    fmap[eip] = fmap[eip] + i.length
    if i.misc["opdsz"] == 16:
        fmap[dst[0:8]] = _t[8:16]
        fmap[dst[8:16]] = _t[0:8]
    else:
        fmap[dst[0:8]] = _t[24:32]
        fmap[dst[8:16]] = _t[16:24]
        fmap[dst[16:24]] = _t[8:16]
        fmap[dst[24:32]] = _t[0:8]


def i_MOVSX(i, fmap):
    op1 = i.operands[0]
    op2 = i.operands[1]
    fmap[eip] = fmap[eip] + i.length
    fmap[op1] = fmap(op2).signextend(op1.size)


def i_MOVZX(i, fmap):
    op1 = i.operands[0]
    op2 = i.operands[1]
    fmap[eip] = fmap[eip] + i.length
    fmap[op1] = fmap(op2).zeroextend(op1.size)


def i_ADC(i, fmap):
    op1 = i.operands[0]
    op2 = fmap(i.operands[1])
    fmap[eip] = fmap[eip] + i.length
    a = fmap(op1)
    c = fmap(cf)
    x, carry, overflow = AddWithCarry(a, op2, c)
    fmap[pf] = parity8(x[0:8])
    fmap[af] = halfcarry(a, op2, c)
    fmap[zf] = x == 0
    fmap[sf] = x < 0
    fmap[cf] = carry
    fmap[of] = overflow
    fmap[op1] = x


def i_ADD(i, fmap):
    op1 = i.operands[0]
    op2 = fmap(i.operands[1])
    fmap[eip] = fmap[eip] + i.length
    a = fmap(op1)
    x, carry, overflow = AddWithCarry(a, op2)
    fmap[pf] = parity8(x[0:8])
    fmap[af] = halfcarry(a, op2)
    fmap[zf] = x == 0
    fmap[sf] = x < 0
    fmap[cf] = carry
    fmap[of] = overflow
    fmap[op1] = x


def i_SBB(i, fmap):
    op1 = i.operands[0]
    op2 = fmap(i.operands[1])
    fmap[eip] = fmap[eip] + i.length
    a = fmap(op1)
    c = fmap(cf)
    x, carry, overflow = SubWithBorrow(a, op2, c)
    fmap[pf] = parity8(x[0:8])
    fmap[af] = halfborrow(a, op2, c)
    fmap[zf] = x == 0
    fmap[sf] = x < 0
    fmap[cf] = carry
    fmap[of] = overflow
    fmap[op1] = x


def i_SUB(i, fmap):
    op1 = i.operands[0]
    op2 = fmap(i.operands[1])
    fmap[eip] = fmap[eip] + i.length
    a = fmap(op1)
    x, carry, overflow = SubWithBorrow(a, op2)
    fmap[pf] = parity8(x[0:8])
    fmap[af] = halfborrow(a, op2)
    fmap[zf] = x == 0
    fmap[sf] = x < 0
    fmap[cf] = carry
    fmap[of] = overflow
    fmap[op1] = x


def i_AND(i, fmap):
    op1 = i.operands[0]
    op2 = fmap(i.operands[1])
    fmap[eip] = fmap[eip] + i.length
    if op2.size < op1.size:
        op2 = op2.signextend(op1.size)
    x = fmap(op1) & op2
    fmap[zf] = x == 0
    fmap[sf] = x < 0
    fmap[cf] = bit0
    fmap[of] = bit0
    fmap[pf] = parity8(x[0:8])
    fmap[op1] = x


def i_OR(i, fmap):
    op1 = i.operands[0]
    op2 = fmap(i.operands[1])
    fmap[eip] = fmap[eip] + i.length
    x = fmap(op1) | op2
    fmap[zf] = x == 0
    fmap[sf] = x < 0
    fmap[cf] = bit0
    fmap[of] = bit0
    fmap[pf] = parity8(x[0:8])
    fmap[op1] = x


def i_XOR(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    op1 = i.operands[0]
    op2 = fmap(i.operands[1])
    x = fmap(op1) ^ op2
    fmap[zf] = x == 0
    fmap[sf] = x < 0
    fmap[cf] = bit0
    fmap[of] = bit0
    fmap[pf] = parity8(x[0:8])
    fmap[op1] = x


def i_CMP(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    op1 = fmap(i.operands[0])
    op2 = fmap(i.operands[1])
    x, carry, overflow = SubWithBorrow(op1, op2)
    fmap[af] = halfborrow(op1, op2)
    fmap[zf] = x == 0
    fmap[sf] = x < 0
    fmap[cf] = carry
    fmap[of] = overflow
    fmap[pf] = parity8(x[0:8])


def i_CMPXCHG(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    dst, src = i.operands
    acc = {8: al, 16: ax, 32: eax}[dst.size]
    t = fmap(acc == dst)
    fmap[zf] = tst(t, bit1, bit0)
    v = fmap(dst)
    fmap[dst] = tst(t, fmap(src), v)
    fmap[acc] = v


def i_CMPXCHG8B(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    dst = i.operands[0]
    src = composer([ebx, ecx])
    acc = composer([eax, edx])
    t = fmap(acc == dst)
    fmap[zf] = tst(t, bit1, bit0)
    v = fmap(dst)
    fmap[dst] = tst(t, fmap(src), v)
    fmap[eax] = v[0:32]
    fmap[edx] = v[32:64]


def i_TEST(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    op1 = fmap(i.operands[0])
    op2 = fmap(i.operands[1])
    x = op1 & op2
    fmap[zf] = x == 0
    fmap[sf] = x[x.size - 1 : x.size]
    fmap[cf] = bit0
    fmap[of] = bit0
    fmap[pf] = parity8(x[0:8])


def i_LEA(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    op1 = i.operands[0]
    op2 = i.operands[1]
    # "effective" address is agnostic of segmentation/pagination
    # so we don't want to compute op2.addr(fmap)
    adr = fmap(op2.a.base + op2.a.disp)
    if op1.size > adr.size:
        adr = adr.zeroextend(op1.size)
    elif op1.size < adr.size:
        adr = adr[0 : op1.size]
    fmap[op1] = adr


def i_XCHG(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    op1 = i.operands[0]
    op2 = i.operands[1]
    tmp = fmap(op1)
    fmap[op1] = fmap(op2)
    fmap[op2] = tmp


def i_SHR(i, fmap):
    op1 = i.operands[0]
    count = fmap(i.operands[1] & 0x1F)
    fmap[eip] = fmap[eip] + i.length
    a = fmap(op1)
    if count._is_cst:
        if count.value == 0:
            return  # flags unchanged
        if count.value == 1:
            fmap[of] = a.bit(-1)  # MSB of a
        else:
            fmap[of] = top(1)
        if count.value <= a.size:
            fmap[cf] = a.bit(count.value - 1)
        else:
            fmap[cf] = bit0
    else:
        fmap[cf] = top(1)
        fmap[of] = top(1)
    res = a >> count
    fmap[op1] = res
    fmap[sf] = res < 0
    fmap[zf] = res == 0
    fmap[pf] = parity8(res[0:8])


def i_SAR(i, fmap):
    op1 = i.operands[0]
    count = fmap(i.operands[1] & 0x1F)
    fmap[eip] = fmap[eip] + i.length
    a = fmap(op1)
    if count._is_cst:
        if count.value == 0:
            return
        if count.value == 1:
            fmap[of] = bit0
        else:
            fmap[of] = top(1)
        if count.value <= a.size:
            fmap[cf] = a.bit(count.value - 1)
        else:
            fmap[cf] = a.bit(-1)
    else:
        fmap[cf] = top(1)
        fmap[of] = top(1)
    res = a // count  # (// is used as arithmetic shift in cas.py)
    fmap[op1] = res
    fmap[sf] = res < 0
    fmap[zf] = res == 0
    fmap[pf] = parity8(res[0:8])


def i_SHL(i, fmap):
    op1 = i.operands[0]
    count = fmap(i.operands[1] & 0x1F)
    fmap[eip] = fmap[eip] + i.length
    a = fmap(op1)
    x = a << count
    if count._is_cst:
        if count.value == 0:
            return
        if count.value == 1:
            fmap[of] = x.bit(-1) ^ fmap(cf)
        else:
            fmap[of] = top(1)
        if count.value <= a.size:
            fmap[cf] = a.bit(a.size - count.value)
        else:
            fmap[cf] = bit0
    else:
        fmap[cf] = top(1)
        fmap[of] = top(1)
    fmap[op1] = x
    fmap[sf] = x < 0
    fmap[zf] = x == 0
    fmap[pf] = parity8(x[0:8])


i_SAL = i_SHL


def i_ROL(i, fmap):
    op1 = i.operands[0]
    size = op1.size
    count = fmap(i.operands[1] & 0x1F) % size
    fmap[eip] = fmap[eip] + i.length
    a = fmap(op1)
    x = ROL(a, count)
    if count._is_cst:
        if count.value == 0:
            return
        fmap[cf] = x.bit(0)
        if count.value == 1:
            fmap[of] = x.bit(-1) ^ fmap(cf)
        else:
            fmap[of] = top(1)
    else:
        fmap[cf] = top(1)
        fmap[of] = top(1)
    fmap[op1] = x


def i_ROR(i, fmap):
    op1 = i.operands[0]
    size = op1.size
    count = fmap(i.operands[1] & 0x1F) % size
    fmap[eip] = fmap[eip] + i.length
    a = fmap(op1)
    x = ROR(a, count)
    if count._is_cst:
        if count.value == 0:
            return
        fmap[cf] = x.bit(-1)
        if count.value == 1:
            fmap[of] = x.bit(-1) ^ x.bit(-2)
        else:
            fmap[of] = top(1)
    else:
        fmap[cf] = top(1)
        fmap[of] = top(1)
    fmap[op1] = x


def i_RCL(i, fmap):
    op1 = i.operands[0]
    size = op1.size
    if size < 32:
        size = size + 1  # count cf
    count = fmap(i.operands[1] & 0x1F) % size
    fmap[eip] = fmap[eip] + i.length
    a = fmap(op1)
    x, carry = ROLWithCarry(a, count, fmap(cf))
    if count._is_cst:
        if count.value == 0:
            return
        fmap[cf] = carry
        if count.value == 1:
            fmap[of] = x.bit(-1) ^ fmap(cf)
        else:
            fmap[of] = top(1)
    else:
        fmap[cf] = top(1)
        fmap[of] = top(1)
    fmap[op1] = x


def i_RCR(i, fmap):
    op1 = i.operands[0]
    size = op1.size
    if size < 32:
        size = size + 1  # count cf
    count = fmap(i.operands[1] & 0x1F) % size
    fmap[eip] = fmap[eip] + i.length
    a = fmap(op1)
    x, carry = RORWithCarry(a, count, fmap(cf))
    if count._is_cst:
        if count.value == 0:
            return
        if count.value == 1:
            fmap[of] = a.bit(-1) ^ fmap(cf)
        else:
            fmap[of] = top(1)
    else:
        fmap[cf] = top(1)
        fmap[of] = top(1)
    fmap[cf] = carry
    fmap[op1] = x


def i_CMOVcc(i, fmap):
    op1 = i.operands[0]
    op2 = fmap(i.operands[1])
    fmap[eip] = fmap[eip] + i.length
    a = fmap(op1)
    fmap[op1] = tst(fmap(i.cond[1]), op2, a)


def i_SHRD(i, fmap):
    op1 = i.operands[0]
    op2 = fmap(i.operands[1])
    op3 = fmap(i.operands[2])
    fmap[eip] = fmap[eip] + i.length
    if not op3._is_cst:
        x = top(op1.size)
    else:
        n = op3.value
        r = op1.size - n
        x = (fmap(op1) >> n) | (op2 << r)
    fmap[op1] = x
    fmap[sf] = x < 0
    fmap[zf] = x == 0
    fmap[pf] = parity8(x[0:8])


def i_SHLD(i, fmap):
    op1 = i.operands[0]
    op2 = fmap(i.operands[1])
    op3 = fmap(i.operands[2])
    fmap[eip] = fmap[eip] + i.length
    if not op3._is_cst:
        x = top(op1.size)
    else:
        n = op3.value
        r = op1.size - n
        x = (fmap(op1) << n) | (op2 >> r)
    fmap[op1] = x
    fmap[sf] = x < 0
    fmap[zf] = x == 0
    fmap[pf] = parity8(x[0:8])


def i_IMUL(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    if len(i.operands) == 1:
        src = i.operands[0]
        m, d = {8: (al, ah), 16: (ax, dx), 32: (eax, edx)}[src.size]
        r = fmap(m**src)
    elif len(i.operands) == 2:
        dst, src = i.operands
        m = d = dst
        r = fmap(dst**src)
    else:
        dst, src, imm = i.operands
        m = d = dst
        r = fmap(src) ** imm.signextend(src.size)
    lo = r[0 : src.size]
    hi = r[src.size : r.size]
    fmap[d] = hi
    fmap[m] = lo
    fmap[cf] = hi != (lo >> 31)
    fmap[of] = hi != (lo >> 31)


def i_MUL(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    src = i.operands[0]
    m, d = {8: (al, ah), 16: (ax, dx), 32: (eax, edx)}[src.size]
    r = fmap(m**src)
    lo = r[0 : src.size]
    hi = r[src.size : r.size]
    fmap[d] = hi
    fmap[m] = lo
    fmap[cf] = hi != 0
    fmap[of] = hi != 0


def i_DIV(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    src = i.operands[0]
    m, d = {8: (al, ah), 16: (ax, dx), 32: (eax, edx)}[src.size]
    md_ = composer([m, d])
    s_ = src.zeroextend(md_.size)
    q_ = fmap(md_ / s_)
    r_ = fmap(md_ % s_)
    fmap[d] = r_[0 : d.size]
    fmap[m] = q_[0 : m.size]


def i_IDIV(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    src = i.operands[0]
    m, d = {8: (al, ah), 16: (ax, dx), 32: (eax, edx)}[src.size]
    md_ = composer([m, d])
    md_.sf = True
    s_ = src.signextend(md_.size)
    q_ = fmap(md_ / s_)
    r_ = fmap(md_ % s_)
    fmap[d] = r_[0 : d.size]
    fmap[m] = q_[0 : m.size]


def i_RDRAND(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    dst = i.operands[0]
    fmap[dst] = top(dst.size)
    fmap[cf] = top(1)
    for f in (of, sf, zf, af, pf):
        fmap[f] = bit0


def i_MOVNTI(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    dst, src = i.operands
    fmap[dst] = fmap(src)


def i_CRC32(i, fmap):
    logger.verbose("%s semantic is not defined" % i.mnemonic)
    fmap[eip] = fmap[eip] + i.length
    dst = i.operands[0]
    fmap[dst] = top(dst.size)


def i_RDTSC(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    fmap[edx] = top(32)
    fmap[eax] = top(32)


def i_RDTSCP(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    fmap[edx] = top(32)
    fmap[eax] = top(32)
    fmap[ecx] = top(32)


def i_CLTS(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    fmap[TS] = bit0


def i_CPUID(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    # EAX 0 returns maximum input eax value and vendor id:
    v = fmap(eax)
    if v._is_cst:
        if v == 0:
            fmap[eax] = cst(0x02, 32)
            fmap[ebx] = cst(struct.unpack("<I", b"Genu")[0], 32)
            fmap[ecx] = cst(struct.unpack("<I", b"ntel")[0], 32)
            fmap[edx] = cst(struct.unpack("<I", b"ineI")[0], 32)
        elif v == 1:
            fmap[eax] = cst(0, 32)
            fmap[eax[0:8]] = cst(0xF2, 8)
            fmap[eax[8:16]] = cst(0x05, 8)
            fmap[ebx] = top(32)
            fmap[ecx] = top(32)
            fmap[edx] = top(32)
        elif v == 2:
            fmap[eax] = cst(0x665B5010, 32)
            fmap[ebx] = cst(0, 32)
            fmap[ecx] = cst(0, 32)
            fmap[edx] = cst(0x007A7000, 32)
    else:
        fmap[eax] = top(32)
        fmap[ebx] = top(32)
        fmap[ecx] = top(32)
        fmap[edx] = top(32)


def i_BOUND(i, fmap):
    logger.verbose("%s semantic is not defined" % i.mnemonic)
    fmap[eip] = fmap[eip] + i.length
    # #UD #BR exceptions not implemented


def i_LFENCE(i, fmap):
    logger.verbose("%s semantic is not defined" % i.mnemonic)
    fmap[eip] = fmap[eip] + i.length


def i_MFENCE(i, fmap):
    logger.verbose("%s semantic is not defined" % i.mnemonic)
    fmap[eip] = fmap[eip] + i.length


def i_SFENCE(i, fmap):
    logger.verbose("%s semantic is not defined" % i.mnemonic)
    fmap[eip] = fmap[eip] + i.length


def i_LGDT(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    src = i.operands[0]
    desc = fmap(src)
    # no translation of base address, desc
    # holds the limit and linear address already
    fmap[GDTR] = desc.zeroextend(GDTR.size)


def i_SGDT(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    dst = i.operands[0]
    fmap[dst] = fmap(GDTR)


def i_LIDT(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    src = i.operands[0]
    desc = fmap(src)
    # no translation of base address, desc
    # holds the limit and linear address already
    fmap[IDTR] = desc.zeroextend(IDTR.size)


def i_SIDT(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    dst = i.operands[0]
    fmap[dst] = fmap(IDTR)


def i_LLDT(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    src = i.operands[0]
    sel = fmap(src[0:16])
    fmap[LDTR] = sel
    # update hidden parts if the concrete descritor exists in GDT:
    if ldt_s := sel & (~0x7):
        e = read_descriptor(fmap, ldt_s)
        if e is not None and e.type == DESC_LDT:
            fmap[seglimit(LDTR)] = cst(e.limit(), 16)
            fmap[segbase(LDTR)] = cst(e.base(), 32)


def i_SLDT(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    dst = i.operands[0]
    fmap[dst] = fmap(LDTR)


def i_LMSW(i, fmap):
    assert internals["ring"] == 0
    fmap[eip] = fmap[eip] + i.length
    src = fmap(i.operands[0])
    if src[0:1] == bit1:
        fmap[PE] = bit1
    fmap[MP] = src[1:2]
    fmap[EM] = src[2:3]
    fmap[TS] = src[3:4]


def i_SMSW(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    dst = i.operands[0]
    fmap[dst] = fmap(cr0[0 : dst.size])


def i_BSF(i, fmap):
    logger.verbose("%s semantic is not defined" % i.mnemonic)
    fmap[eip] = fmap[eip] + i.length
    dst, src = i.operands
    x = fmap(src)
    fmap[zf] = x == 0
    fmap[dst] = top(dst.size)


def i_BSR(i, fmap):
    logger.verbose("%s semantic is not defined" % i.mnemonic)
    fmap[eip] = fmap[eip] + i.length
    dst, src = i.operands
    x = fmap(src)
    fmap[zf] = x == 0
    fmap[dst] = top(dst.size)


def i_POPCNT(i, fmap):
    logger.verbose("%s semantic is not defined" % i.mnemonic)
    dst, src = i.operands
    fmap[dst] = top(dst.size)
    fmap[cf] = bit0
    fmap[of] = bit0
    fmap[sf] = bit0
    fmap[af] = bit0
    fmap[zf] = fmap(src) == 0
    fmap[eip] = fmap[eip] + i.length


def i_LZCNT(i, fmap):
    logger.verbose("%s semantic is not defined" % i.mnemonic)
    dst, _ = i.operands
    fmap[dst] = top(dst.size)
    fmap[cf] = fmap[zf] = top(1)
    fmap[eip] = fmap[eip] + i.length


def i_TZCNT(i, fmap):
    logger.verbose("%s semantic is not defined" % i.mnemonic)
    dst, _ = i.operands
    fmap[dst] = top(dst.size)
    fmap[cf] = fmap[zf] = top(1)
    fmap[eip] = fmap[eip] + i.length


def i_BT(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    src, idx = i.operands
    off = fmap(idx)
    if off._is_cst:
        fmap[cf] = fmap(src[off.v : off.v + 1])
    else:
        fmap[cf] = top(1)


def i_BTC(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    src, idx = i.operands
    off = fmap(idx)
    if off._is_cst:
        dst = src[off.v : off.v + 1]
        fmap[cf] = fmap(dst)
        fmap[dst] = ~fmap[cf]
    else:
        fmap[cf] = top(1)
        fmap[src] = top(src.size)


def i_BTR(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    src, idx = i.operands
    off = fmap(idx)
    if off._is_cst:
        dst = src[off.v : off.v + 1]
        fmap[cf] = fmap(dst)
        fmap[dst] = bit0
    else:
        fmap[cf] = top(1)
        fmap[src] = top(src.size)


def i_BTS(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    src, idx = i.operands
    off = fmap(idx)
    if off._is_cst:
        dst = src[off.v : off.v + 1]
        fmap[cf] = fmap(dst)
        fmap[dst] = bit1
    else:
        fmap[cf] = top(1)
        fmap[src] = top(src.size)


def i_CLFLUSH(i, fmap):
    logger.verbose("%s semantic is not defined" % i.mnemonic)
    fmap[eip] = fmap[eip] + i.length
    # cache not supported


def i_INVD(i, fmap):
    logger.verbose("%s semantic is not defined" % i.mnemonic)
    fmap[eip] = fmap[eip] + i.length
    # cache not supported


def i_WBINVD(i, fmap):
    logger.verbose("%s semantic is not defined" % i.mnemonic)
    fmap[eip] = fmap[eip] + i.length
    # cache not supported


def i_INVLPG(i, fmap):
    pgaddr = fmap(i.operands[0])
    if pgaddr._is_cst:
        addr = pgaddr.v
    pd_, pt_, pte = mmu_get_info(fmap, addr)
    pde = pd_[addr >> 22]
    pt_base = pde.address << 12
    if pt_base in mmu_cache:
        del mmu_cache[pt_base]
    fmap[eip] = fmap[eip] + i.length


def i_CLI(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    fmap[If] = bit0


def i_STI(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    fmap[If] = bit1


def i_PREFETCHT0(i, fmap):
    logger.verbose("%s semantic is not defined" % i.mnemonic)
    fmap[eip] = fmap[eip] + i.length
    # interruptions not supported


def i_PREFETCHT1(i, fmap):
    logger.verbose("%s semantic is not defined" % i.mnemonic)
    fmap[eip] = fmap[eip] + i.length
    # interruptions not supported


def i_PREFETCHT2(i, fmap):
    logger.verbose("%s semantic is not defined" % i.mnemonic)
    fmap[eip] = fmap[eip] + i.length
    # interruptions not supported


def i_PREFETCHNTA(i, fmap):
    logger.verbose("%s semantic is not defined" % i.mnemonic)
    fmap[eip] = fmap[eip] + i.length
    # interruptions not supported


def i_PREFETCHW(i, fmap):
    logger.verbose("%s semantic is not defined" % i.mnemonic)
    fmap[eip] = fmap[eip] + i.length
    # interruptions not supported


def i_LAR(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    dst, src = i.operands
    if src._is_cst:
        e = read_descriptor(fmap, src)
        if e is not None and e.s == DESC_SEGMENT:
            fmap[zf] = bit1
            fmap[dst[0:16]] = composer(
                [cst(0, 8), cst(e.type, 4), cst(e.s, 1), cst(e.dpl, 2), cst(e.p, 1)]
            )
            if dst.size > 16:
                fmap[dst[20:24]] = composer(
                    [cst(e.avl, 1), cst(e.l, 1), cst(e.d, 1), cst(e.g, 1)]
                )
                fmap[dst[24:32]] = cst(0, 8)
    else:
        fmap[zf] = top(1)
        fmap[dst] = top(dst.size)


def i_STR(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    dst = i.operands[0]
    src = fmap(TR)
    if dst._is_reg:
        fmap[dst] = src.zeroextend(dst)
    else:
        dst.size = 16
        fmap[dst] = fmap(TR)


def i_RDMSR(i, fmap):
    logger.verbose("%s semantic is not defined" % i.mnemonic)
    fmap[eip] = fmap[eip] + i.length


def i_WRMSR(i, fmap):
    logger.verbose("%s semantic is not defined" % i.mnemonic)
    fmap[eip] = fmap[eip] + i.length


def i_RDPMC(i, fmap):
    logger.verbose("%s semantic is not defined" % i.mnemonic)
    fmap[eip] = fmap[eip] + i.length


def i_RSM(i, fmap):
    logger.verbose("%s semantic is not defined" % i.mnemonic)
    fmap[eip] = fmap[eip] + i.length


def i_MONITOR(i, fmap):
    logger.verbose("%s semantic is not defined" % i.mnemonic)
    fmap[eip] = fmap[eip] + i.length


def i_XGETBV(i, fmap):
    logger.verbose("%s semantic is not defined" % i.mnemonic)
    fmap[eip] = fmap[eip] + i.length


def i_XSETBV(i, fmap):
    logger.verbose("%s semantic is not defined" % i.mnemonic)
    fmap[eip] = fmap[eip] + i.length


def i_FXSAVE(i, fmap):
    logger.verbose("%s semantic is not defined" % i.mnemonic)
    fmap[eip] = fmap[eip] + i.length


def i_FXRSTOR(i, fmap):
    logger.verbose("%s semantic is not defined" % i.mnemonic)
    fmap[eip] = fmap[eip] + i.length


def i_LDMXCSR(i, fmap):
    logger.verbose("%s semantic is not defined" % i.mnemonic)
    fmap[eip] = fmap[eip] + i.length


def i_STMXCSR(i, fmap):
    logger.verbose("%s semantic is not defined" % i.mnemonic)
    fmap[eip] = fmap[eip] + i.length


def i_XSAVE(i, fmap):
    logger.verbose("%s semantic is not defined" % i.mnemonic)
    fmap[eip] = fmap[eip] + i.length


def i_XRSTOR(i, fmap):
    logger.verbose("%s semantic is not defined" % i.mnemonic)
    fmap[eip] = fmap[eip] + i.length


def i_XSAVEOPT(i, fmap):
    logger.verbose("%s semantic is not defined" % i.mnemonic)
    fmap[eip] = fmap[eip] + i.length


def i_SYSENTER(i, fmap):
    logger.verbose("%s semantic is not defined" % i.mnemonic)
    fmap[eip] = top(32)
    fmap[esp] = top(32)
    fmap[cs] = top(16)
    fmap[ss] = top(16)


def i_SYSEXIT(i, fmap):
    logger.verbose("%s semantic is not defined" % i.mnemonic)
    fmap[eip] = top(32)
    fmap[esp] = top(32)
    fmap[cs] = top(16)
    fmap[ss] = top(16)


def i_PAND(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    op1 = i.operands[0]
    op2 = fmap(i.operands[1])
    x = fmap(op1) & op2
    fmap[op1] = x


def i_PANDN(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    op1 = i.operands[0]
    op2 = fmap(i.operands[1])
    x = fmap(~op1) & op2
    fmap[op1] = x


def i_POR(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    op1 = i.operands[0]
    op2 = fmap(i.operands[1])
    x = fmap(op1) | op2
    fmap[op1] = x


def i_PXOR(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    op1 = i.operands[0]
    op2 = fmap(i.operands[1])
    x = fmap(op1) ^ op2
    fmap[op1] = x


i_ANDPS = i_PAND
i_ANDNPS = i_PANDN
i_ORPS = i_POR
i_XORPS = i_PXOR


def i_MOVD(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    op1 = i.operands[0]
    op2 = fmap(i.operands[1])
    fmap[op1] = op2[0:32].zeroextend(op1.size)


def i_MOVQ(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    op1 = i.operands[0]
    op2 = fmap(i.operands[1])
    fmap[op1] = op2[0:64].zeroextend(op1.size)


def sse_MOVSD(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    op1 = i.operands[0]
    op2 = i.operands[1]
    if op1._is_mem:
        src = fmap(op2[0 : op1.size])
    elif op2._is_mem:
        src = fmap(op2).zeroextend(op1.size)
    fmap[op1] = src


def i_MOVDQU(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    op1 = i.operands[0]
    op2 = i.operands[1]
    fmap[op1] = fmap(op2)


def i_MOVDQA(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    op1 = i.operands[0]
    op2 = i.operands[1]
    fmap[op1] = fmap(op2)


def i_MOVUPS(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    op1 = i.operands[0]
    op2 = i.operands[1]
    fmap[op1] = fmap(op2)


def i_MOVAPS(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    op1 = i.operands[0]
    op2 = i.operands[1]
    fmap[op1] = fmap(op2)


def i_PADDB(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    op1 = i.operands[0]
    op2 = i.operands[1]
    assert op1.size == op2.size
    for __i in range(0, op1.size, 8):
        src1 = fmap(op1[__i : __i + 8])
        src2 = fmap(op2[__i : __i + 8])
        fmap[op1[__i : __i + 8]] = src1 + src2


def i_PSUBUSB(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    op1 = i.operands[0]
    op2 = i.operands[1]
    assert op1.size == op2.size
    for __i in range(0, op1.size, 8):
        src1 = fmap(op1[__i : __i + 8])
        src2 = fmap(op2[__i : __i + 8])
        res = src1 - src2
        fmap[op1[__i : __i + 8]] = tst(src1 < src2, cst(0, op1.size), res)


def i_PMAXUB(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    op1 = i.operands[0]
    op2 = i.operands[1]
    assert op1.size == op2.size
    for __i in range(0, op1.size, 8):
        src1 = fmap(op1[__i : __i + 8])
        src2 = fmap(op2[__i : __i + 8])
        fmap[op1[__i : __i + 8]] = tst(src1 > src2, src1, src2)


def i_PMINUB(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    op1 = i.operands[0]
    op2 = i.operands[1]
    assert op1.size == op2.size
    for __i in range(0, op1.size, 8):
        src1 = fmap(op1[__i : __i + 8])
        src2 = fmap(op2[__i : __i + 8])
        fmap[op1[__i : __i + 8]] = tst(src1 < src2, src1, src2)


def i_PUNPCKHBW(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    op1 = i.operands[0]
    op2 = i.operands[1]
    assert op1.size == op2.size
    src1 = fmap(op1)
    src2 = fmap(op2)
    val1 = (src1[i : i + 8] for i in range(0, op1.size, 8))
    val2 = (src2[i : i + 8] for i in range(0, op2.size, 8))
    res = [composer([v1, v2]) for (v1, v2) in zip(val1, val2)]
    fmap[op1] = composer(res)[op1.size : 2 * op1.size]


def i_PUNPCKLBW(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    op1 = i.operands[0]
    op2 = i.operands[1]
    assert op1.size == op2.size
    src1 = fmap(op1)
    src2 = fmap(op2)
    val1 = (src1[i : i + 8] for i in range(0, op1.size, 8))
    val2 = (src2[i : i + 8] for i in range(0, op2.size, 8))
    res = [composer([v1, v2]) for (v1, v2) in zip(val1, val2)]
    fmap[op1] = composer(res)[0 : op1.size]


def i_PCMPEQB(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    op1 = i.operands[0]
    op2 = i.operands[1]
    assert op1.size == op2.size
    src1 = fmap(op1)
    src2 = fmap(op2)
    val1 = (src1[i : i + 8] for i in range(0, op1.size, 8))
    val2 = (src2[i : i + 8] for i in range(0, op2.size, 8))
    res = [tst(v1 == v2, cst(0xFF, 8), cst(0, 8)) for (v1, v2) in zip(val1, val2)]
    fmap[op1] = composer(res)


def i_PSRLW(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    op1 = i.operands[0]
    op2 = i.operands[1]
    src1 = fmap(op1)
    src2 = fmap(op2)
    val1 = (src1[i : i + 16] for i in range(0, op1.size, 16))
    res = [v1 >> src2 for v1 in val1]
    fmap[op1] = composer(res)


def i_PSRLD(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    op1 = i.operands[0]
    op2 = i.operands[1]
    src1 = fmap(op1)
    src2 = fmap(op2)
    val1 = (src1[i : i + 32] for i in range(0, op1.size, 32))
    res = [v1 >> src2 for v1 in val1]
    fmap[op1] = composer(res)


def i_PSRLQ(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    op1 = i.operands[0]
    op2 = i.operands[1]
    src1 = fmap(op1)
    src2 = fmap(op2)
    val1 = (src1[i : i + 64] for i in range(0, op1.size, 64))
    res = [v1 >> src2 for v1 in val1]
    fmap[op1] = composer(res)


def i_PSLLQ(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    op1 = i.operands[0]
    op2 = i.operands[1]
    src1 = fmap(op1)
    src2 = fmap(op2)
    val1 = (src1[i : i + 64] for i in range(0, op1.size, 64))
    res = [v1 << src2 for v1 in val1]
    fmap[op1] = composer(res)


def i_PSHUFD(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    op1 = i.operands[0]
    op2 = i.operands[1]
    op3 = i.operands[2]
    assert op1.size == op2.size == 128
    sz = 2
    dst = []
    src = fmap(op2)
    order = fmap(op3)
    j = 0
    for i in range(0, op1.size, 32):
        dst.append((src >> (order[j : j + sz] * 32))[0:32])
        j += sz
    fmap[op1] = composer(dst)


def i_PSHUFB(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    op1 = i.operands[0]
    op2 = i.operands[1]
    assert op1.size == op2.size
    sz = 4 if op1.size == 128 else 3
    src = fmap(op1)
    mask = fmap(op2)
    for i in range(0, op1.size, 8):
        srcb = src[i : i + 8]
        maskb = mask[i : i + 8]
        indx = maskb[0:sz]
        if indx._is_cst:
            sta, sto = indx.value * 8, indx.value * 8 + 8
            v = src[sta:sto]
            src[i : i + 8] = tst(maskb[7:8], cst(0, 8), v)
            src[sta:sto] = tst(maskb[7:8], v, srcb)
        else:
            src[i : i + 8] = tst(maskb[7:8], cst(0, 8), top(8))
    fmap[op1] = src


def i_PINSRW(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    op1 = i.operands[0]
    op2 = i.operands[1]
    op3 = i.operands[2]
    if op2._is_reg:
        op2 = op2[0:16]
    src1 = fmap(op1)
    src2 = fmap(op2)
    if op3._is_cst:
        sta, sto = op3.value * 16, op3.value * 16 + 16
        src1[sta:sto] = src2
    else:
        src1 = top(src1.size)
    fmap[op1] = src1


def i_PEXTRW(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    op1 = i.operands[0]
    op2 = i.operands[1]
    op3 = i.operands[2]
    src2 = fmap(op2)
    if op3._is_cst:
        sta, sto = op3.value * 16, op3.value * 16 + 16
        v = src2[sta:sto]
    else:
        v = top(16)
    fmap[op1] = v.zeroextend(op1.size)


i_ENDBR32 = i_NOP
i_ENDBR64 = i_NOP
i_FNINIT = i_FNSTENV = i_FNSTCW = i_FNSAVE = i_FNSTSW = i_FNCLEX = i_FNOP = i_NOP


def i_VERR(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    op1 = i.operands[0]
    if not op1._is_cst:
        op1 = fmap(op1.a.seg or ds)
    rpl = op1 & 7
    selector = op1
    e = read_descriptor(fmap, selector)
    if e is None:
        fmap[zf] = top(1)
    else:
        cpl = internals["ring"]
        if e.s == 0 or ((e.type < 12) and ((cpl > e.dpl) or (rpl > e.dpl))):
            fmap[zf] = bit0
        else:
            if e.type in (SEG_XO, SEG_XO_a, SEG_XO_e, SEG_XO_ea):
                fmap[zf] = bit0
            else:
                fmap[zf] = bit1


def i_VERW(i, fmap):
    fmap[eip] = fmap[eip] + i.length
    op1 = i.operands[0]
    if not op1._is_cst:
        op1 = fmap(op1.a.seg or ds)
    rpl = op1 & 3
    selector = op1
    e = read_descriptor(fmap, selector)
    if e is None:
        fmap[zf] = top(1)
    else:
        cpl = internals["ring"]
        if e.s == 0 or ((e.type < 12) and ((cpl > e.dpl) or (rpl > e.dpl))):
            fmap[zf] = bit0
        else:
            if e.type in (SEG_RW, SEG_RW_a, SEG_RW_e, SEG_RW_ea):
                fmap[zf] = bit1
            else:
                fmap[zf] = bit0
