# -*- coding: utf-8 -*-

# This code is part of Amoco
# Copyright (C) 2006-2011 Axel Tillequin (bdcht3@gmail.com)
# published under GPLv2 license

from amoco.cas.expressions import tst, comp, cst, ror


def stst(*args, **kargs):
    return tst(*args, **kargs).simplify()


def LSL_C(x, shift):
    assert shift >= 0
    carry_out = x.bit(-shift) if shift > 0 else None
    return (x << shift, carry_out)


def LSL(x, shift):
    assert shift >= 0
    return x << shift


def LSR_C(x, shift):
    assert shift >= 0
    if shift == 0:
        return (x, None)
    carry_out = x.bit(shift - 1) if shift < x.size else 0
    return (x >> shift, carry_out)


def LSR(x, shift):
    assert shift >= 0
    return x >> shift


def ASR_C(x, shift):
    assert shift >= 0
    n = x.size
    xx = x.signextend(n + shift)
    carry_out = xx.bit(shift - 1) if shift > 0 else None
    return (xx[shift : shift + n], carry_out)


def ASR(x, shift):
    assert shift >= 0
    n = x.size
    xx = x.signextend(n + shift)
    return xx[shift : shift + n]


def ROR_C(x, shift):
    assert shift != 0
    n = x.size
    m = shift % n
    res = LSR(x, m) | LSL(x, n - m)
    return (res, res.bit(n - 1))


def ROR(x, shift):
    assert shift != 0
    n = x.size
    m = shift % n
    res = LSR(x, m) | LSL(x, n - m)
    return res


def RRX_C(x, carry_in):
    carry_out = x.bit(0)
    res = comp(x.size)
    res[0 : x.size - 1] = x[1 : x.size]
    res[x.size - 1 : x.size] = carry_in
    return (res, carry_out)


def RRX(x, carry_in):
    res = comp(x.size)
    res[0 : x.size - 1] = x[1 : x.size]
    res[x.size - 1 : x.size] = carry_in
    return res


def Shift_C(x, stype, shift, carry_in):
    if shift == 0:
        return (x, carry_in)
    if stype == 0:
        return LSL_C(x, shift)
    elif stype == 1:
        return LSR_C(x, shift)
    elif stype == 2:
        return ASR_C(x, shift)
    elif stype == 3:
        return ROR_C(x, shift)
    elif stype == 4:
        return RRX_C(x, carry_in)


# reg is an instance of reg expression, shift is an integer or reg.
def DecodeShift(stype, reg, shift):
    if stype == 0:
        return reg << shift
    elif stype == 1:
        return reg >> 32 if shift == 0 else reg >> shift
    elif stype == 2:
        return reg // 32 if shift == 0 else reg // shift
    elif stype == 3:
        return reg >> 1 if shift == 0 else ror(reg, shift)


def ARMExpandImm(x):
    v = cst(x & 0xFF, 32)
    return _ror2(v, (x >> 8) & 0xF)


def ARMExpandImm_C(x):
    v = ARMExpandImm(x)
    return (v, v.bit(31))


def ThumbExpandImm(imm12):
    x = int(imm12, 2)
    if (x >> 10) & 3 == 0:
        s = (x >> 8) & 3
        if s == 0b00:
            return cst(x & 0xFF, 32)
        elif s == 0b01:
            if x & 0xFF == 0:
                raise ValueError
            tmp = x & 0xFF
            imm32 = (tmp << 16) | tmp
        elif s == 0b10:
            if x & 0xFF == 0:
                raise ValueError
            tmp = (x & 0xFF) << 8
            imm32 = (tmp << 16) | tmp
        elif s == 0b11:
            if x & 0xFF == 0:
                raise ValueError
            tmp = x & 0xFF
            tmp2 = (tmp << 8) | tmp
            imm32 = (tmp2 << 16) | tmp2
        else:
            raise ValueError(s)
        return cst(imm32, 32)
    else:
        v = cst((1 << 7) | (x & 0x7F), 32)
        return _ror(v, (x >> 7) & 0x1F)


def ITAdvance(itstate):
    if itstate & 7 == 0:
        return 0
    else:
        it_hi = itstate & 0b11100000
        it_lo = itstate & 0xF
        return it_hi | (it_lo << 1)


def InITBlock(itstate):
    return (itstate & 0xF) != 0


def LastInITBlock(itstate):
    return (itstate & 0xF) == 0b1000


def _ror(x, n):
    xx = x & 0xFFFFFFFF
    return ((xx >> n) | (xx << (32 - n))) & 0xFFFFFFFF


def _ror2(x, n):
    xx = x & 0xFFFFFFFF
    nn = n + n
    return ((xx >> nn) | (xx << (32 - nn))) & 0xFFFFFFFF


def BadReg(r):
    return r == 13 or r == 15
