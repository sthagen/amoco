# -*- coding: utf-8 -*-

# This code is part of Amoco
# Copyright (C) 2013 Axel Tillequin (bdcht3@gmail.com)
# published under GPLv2 license

# spec_xxx files are providers for instruction objects.
# These objects are wrapped and created by disasm.py.

from amoco.arch.arm.v8 import env64 as env

from amoco.arch.core import ispec, InstructionError
from amoco.arch.core import (
    type_data_processing,
)

# ruff: noqa: F811

def ExtendReg(r, etype, shift=0):
    assert shift >= 0 and shift <= 4
    N = r.size
    signed = True if etype & 4 == 0 else False
    l = 8 << (etype & 3)
    l = min(l, N - shift)
    return r[0:l].extend(signed, N) << shift

def sp2z(x):
    if x is env.sp:
        return env.xzr
    if x is env.wsp:
        return env.wzr
    return x

# ------------------------------------------------------
# amoco ARMv8-A SIMD instruction specs:
# ------------------------------------------------------

ISPECS = []

@ispec("32[ 0 1 0=U 11110 11 10000 01011 10 Rn(5) Rd(5) ]", mnemonic="ABS")
@ispec("32[ 0 1 0=U 11110 11 11000 11011 10 Rn(5) Rd(5) ]", mnemonic="ADDP")
@ispec("32[ 0 0 0=U 11110 01 10001 10100 00 Rn(5) Rd(5) ]", mnemonic="BFCVT")
def A64_SIMD_scalar(obj, U, Rn, Rd):
    obj.datasize = 64
    regs = env.Vregs
    obj.n = regs[Rn]
    obj.d = regs[Rd]
    obj.operands = [obj.d, obj.n]
    obj.U = U
    obj.type = type_data_processing

@ispec("32[ 0 Q 0 01110 size(2) 10000 01011 10 Rn(5) Rd(5) ]", mnemonic="ABS")
def A64_SIMD_vector(obj, Q, size, Rn, Rd):
    if size==3 and Q==0:
        InstructionError
    obj.esize = 8<<size
    obj.datasize = 128 if Q==1 else 64
    regs = env.Vregs
    obj.n = regs[Rn]
    obj.d = regs[Rd]
    obj.operands = [obj.d, obj.n]
    obj.type = type_data_processing

@ispec("32[ 0 Q 0 01110 size(2) 11000 11011 10 Rn(5) Rd(5) ]", mnemonic="ADDV")
def A64_SIMD_vector(obj, Q, size, Rn, Rd):
    if size==3 or (size==2 and Q==0):
        InstructionError
    obj.esize = 8<<size
    obj.datasize = 128 if Q==1 else 64
    regs = env.Vregs
    obj.n = regs[Rn]
    obj.d = regs[Rd]
    obj.operands = [obj.d, obj.n]
    obj.type = type_data_processing

@ispec("32[ 0 1 0=U 11110 11 1 Rm(5) 10000 1 Rn(5) Rd(5) ]", mnemonic="ADD")
def A64_SIMD_scalar(obj, U, Rm, Rn, Rd):
    obj.datasize = 64
    regs = env.Vregs
    obj.m = regs[Rm]
    obj.n = regs[Rn]
    obj.d = regs[Rd]
    obj.operands = [obj.d, obj.n, obj.m]
    obj.U = U
    obj.type = type_data_processing

@ispec("32[ 0 Q 0 01110    size(2) 1 Rm(5) 10000 1 Rn(5) Rd(5) ]", mnemonic="ADD")
@ispec("32[ 0 Q 0 01110    size(2) 1 Rm(5) 10111 1 Rn(5) Rd(5) ]", mnemonic="ADDP")
@ispec("32[ 0 Q 0 01110 00=size(2) 1 Rm(5) 00011 1 Rn(5) Rd(5) ]", mnemonic="AND")
def A64_SIMD_vector(obj, Q, size, Rm, Rn, Rd):
    if size==3 and Q==0:
        InstructionError
    obj.esize = 8<<size
    obj.datasize = 128 if Q==1 else 64
    regs = env.Vregs
    obj.m = regs[Rm]
    obj.n = regs[Rn]
    obj.d = regs[Rd]
    obj.operands = [obj.d, obj.n, obj.m]
    obj.type = type_data_processing

@ispec("32[ 010 01110 00 10100 0010 1 10 Rn(5) Rd(5) ]", mnemonic="AESD")
@ispec("32[ 010 01110 00 10100 0010 0 10 Rn(5) Rd(5) ]", mnemonic="AESE")
@ispec("32[ 010 01110 00 10100 0011 1 10 Rn(5) Rd(5) ]", mnemonic="AESIMC")
@ispec("32[ 010 01110 00 10100 0011 0 10 Rn(5) Rd(5) ]", mnemonic="AESMC")
def A64_SIMD_scalar(obj, Rn, Rd):
    obj.datasize = 64
    regs = env.Vregs
    obj.n = regs[Rn]
    obj.d = regs[Rd]
    obj.operands = [obj.d, obj.n]
    obj.type = type_data_processing

@ispec("32[ 110 0111 00 01 Rm(5) 0 Ra(5) Rn(5) Rd(5) ]", mnemonic="BCAX")
def A64_SIMD_adv(obj, Rm, Ra, Rn, Rd):
    regs = env.Vregs
    obj.a = regs[Ra]
    obj.m = regs[Rm]
    obj.n = regs[Rn]
    obj.d = regs[Rd]
    obj.operands = [obj.d, obj.n, obj.m]
    obj.type = type_data_processing

@ispec(
    "32[ size(2) 111 1 00 -1=opc(2) 0 imm9(9) 01 Rn(5) Rt(5) ]",
    mnemonic="LDR",
    wback=True,
    postindex=True,
)
@ispec(
    "32[ size(2) 111 1 00 -1=opc(2) 0 imm9(9) 11 Rn(5) Rt(5) ]",
    mnemonic="LDR",
    wback=True,
    postindex=False,
)
def A64_SIMD_ldr(obj, size, opc, imm9, Rn, Rt):
    obj.n = sp2z(env.Xregs[Rn])
    obj.scale = (size + (opc>>1)*4)
    obj.datasize = 8<<obj.scale
    obj.offset = env.cst(imm9, 9).signextend(64)
    if obj.datasize>128:
        raise InstructionError
    obj.t = env.Vregs[Rt]
    obj.operands = [obj.t, obj.n, obj.offset]
    obj.type = type_data_processing

@ispec(
    "32[ size(2) 111 1 01 -1=opc(2) imm12(12) Rn(5) Rt(5) ]",
    mnemonic="LDR",
    wback=False,
    postindex=False,
)
def A64_SIMD_ldr(obj, size, opc, imm12, Rn, Rt):
    obj.n = sp2z(env.Xregs[Rn])
    obj.scale = (size + (opc>>1)*4)
    obj.datasize = 8<<obj.scale
    obj.offset = env.cst(imm12, 12).zeroextend(64) << obj.scale
    if obj.datasize>128:
        raise InstructionError
    obj.t = env.Vregs[Rt]
    obj.operands = [obj.t, obj.n, obj.offset]
    obj.type = type_data_processing

@ispec("32[ opc(2) 011 1 00 imm19(19) Rt(5) ]", mnemonic="LDR")
def A64_SIMD_ldr(obj, opc, imm19, Rt):
    obj.size = 4<<opc
    if obj.size>16:
        raise InstructionError
    obj.offset = env.cst(imm19 << 2, 21).signextend(64)
    obj.t = env.Vregs[Rt]
    obj.operands = [obj.t, obj.offset]
    obj.type = type_data_processing

@ispec(
    "32[ size(2) 111 1 00 -1=opc(2) 1 Rm(5) option(3) S 10 Rn(5) Rt(5) ]",
    mnemonic="LDR",
)
def A64_SIMD_ldr(obj, size, opc, Rm, option, S, Rn, Rt):
    obj.wback = False
    obj.postindex = False
    obj.extend_type = option
    obj.n = sp2z(env.Xregs[Rn])
    obj.scale = (size + (opc>>1)*4)
    obj.shift = obj.scale if S == 1 else 0
    obj.datasize = 8<<obj.scale
    if obj.datasize>128 or (option&2 ==0):
        raise InstructionError
    obj.t = env.Vregs[Rt]
    m = sp2z(env.Wregs[Rm]) if option & 1 == 0 else sp2z(env.Xregs[Rm])
    obj.m = ExtendReg(m, option, obj.shift)
    obj.operands = [obj.t, obj.n, obj.m]
    obj.type = type_data_processing
