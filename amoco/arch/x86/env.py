# -*- coding: utf-8 -*-

# This code is part of Amoco
# Copyright (C) 2006-2011 Axel Tillequin (bdcht3@gmail.com)
# published under GPLv2 license

# import expressions:
from amoco.cas.expressions import *

# 32bits registers :
# -------------------

eax = reg("eax", 32)  # accumulator for operands and results data
ebx = reg("ebx", 32)  # pointer to data in the DS segment
ecx = reg("ecx", 32)  # counter for string and loop operations
edx = reg("edx", 32)  # I/O pointer
ebp = reg("ebp", 32)  # pointer to data in the stack (SS segment)
esp = reg("esp", 32)  # stack pointer (SS segment)
esi = reg("esi", 32)  # ptr to data in segment pointed by DS; src ptr for strings
edi = reg("edi", 32)  # ptr to data in segment pointed by ES; dst ptr for strings
eip = reg("eip", 32)  # instruction pointer in 32 bit mode
eflags = reg("eflags", 32)


is_reg_pc(eip)
is_reg_flags(eflags)
is_reg_stack(esp)
is_reg_stack(ebp)
# use variant b for base stack:
ebp.etype |= et_vrb

ax = slc(eax, 0, 16, "ax")
bx = slc(ebx, 0, 16, "bx")
cx = slc(ecx, 0, 16, "cx")
dx = slc(edx, 0, 16, "dx")
bp = slc(ebp, 0, 16, "bp")
sp = slc(esp, 0, 16, "sp")
si = slc(esi, 0, 16, "si")
di = slc(edi, 0, 16, "di")
ip = slc(eip, 0, 16, "ip")

al = slc(eax, 0, 8, "al")
bl = slc(ebx, 0, 8, "bl")
cl = slc(ecx, 0, 8, "cl")
dl = slc(edx, 0, 8, "dl")

ah = slc(eax, 8, 8, "ah")
bh = slc(ebx, 8, 8, "bh")
ch = slc(ecx, 8, 8, "ch")
dh = slc(edx, 8, 8, "dh")

cf = slc(eflags, 0, 1, "cf")  # carry/borrow flag
pf = slc(eflags, 2, 1, "pf")  # parity flag
af = slc(eflags, 4, 1, "af")  # aux carry flag
zf = slc(eflags, 6, 1, "zf")  # zero flag
sf = slc(eflags, 7, 1, "sf")  # sign flag
tf = slc(eflags, 8, 1, "tf")  # trap flag
If = slc(eflags, 9, 1, "if")  # interrupt flag
df = slc(eflags, 10, 1, "df")  # direction flag
of = slc(eflags, 11, 1, "of")  # overflow flag
Nt = slc(eflags, 12, 1, "nt") # nested task

with is_reg_other:
    # segment registers & other mappings:
    cs = reg("cs", 16)  # segment selector for the code segment
    ds = reg("ds", 16)  # segment selector to a data segment
    ss = reg("ss", 16)  # segment selector to the stack segment
    es = reg("es", 16)  # (data)
    fs = reg("fs", 16)  # (data)
    gs = reg("gs", 16)  # (data)

    mmregs = [reg("mm%d" % n, 64) for n in range(8)]

    xmmregs = [reg("xmm%d" % n, 128) for n in range(16)]

# hidden part of the segment registers (aka descriptor cache)
# when an instruction write into a segment reg, this base should
# be updated directly from the correponding descriptor values.
def segbase(s):
    return is_reg_other(reg(s.ref+'_base',32))

def seglimit(s):
    return is_reg_other(reg(s.ref+'_limit',16))

# evaluating a ptr expression that has a segment expression
# will ultimately use this handler to adjust the final base address.
def segment_handler(cls, fmap, s, bd):
    base, disp = bd
    if s is not None:
        sbase = segbase(s).eval(fmap)
        base = sbase + base.zeroextend(sbase.size)
        s = None
    return ptr(base, s, disp)

ptr.segment_handler = segment_handler

# fpu registers (80 bits holds double extended floats see Intel Vol1--4.4.2):
def st(num):
    return is_reg_other(reg("st%d" % num, 80))


# fpu state
fpu_control = reg("fpu_control", 16)
fpu_status = reg("fpu_status", 16)

# return R/M register (see ModR/M Byte encoding) :
def getreg(i, size=32):
    return {
        8: (al, cl, dl, bl, ah, ch, dh, bh),
        16: (ax, cx, dx, bx, sp, bp, si, di),
        32: (eax, ecx, edx, ebx, esp, ebp, esi, edi),
        64: mmregs,
        128: xmmregs[:8],
    }[size][i]


# system registers:

with is_reg_other:
    # control regs:
    cr0 = reg("cr0", 32)
    cr2 = reg("cr2", 32)
    cr3 = reg("cr3", 32)
    cr4 = reg("cr4", 32)
    cr8 = reg("cr8", 32)

    PE = slc(cr0, 0, 1, "PE")   # protected mode enable
    MP = slc(cr0, 1, 1, "MP")   # monitor coprocessor
    EM = slc(cr0, 2, 1, "EM")   # emulate coprocessor
    TS = slc(cr0, 3, 1, "TS")   # task switched
    ET = slc(cr0, 4, 1, "ET")   # extension type
    NE = slc(cr0, 5, 1, "NE")   # numeric error
    WP = slc(cr0,16, 1, "WP")   # write protect
    AM = slc(cr0,18, 1, "AM")   # alignment mask
    NW = slc(cr0,29, 1, "NW")   # not writethrough
    CD = slc(cr0,30, 1, "CD")   # cache disable
    PG = slc(cr0,31, 1, "PG")   # page enable

    PWT = slc(cr3,3, 1, "PWT")
    PCD = slc(cr3,4, 1, "PCD")

    VME = slc(cr4, 0,1, "VME")           # virtual 8086 mode extensions
    PVI = slc(cr4, 1,1, "PVI")           # protected mode virtual interrupts
    TSD = slc(cr4, 2,1, "TSD")           # timestamp disable
    DE  = slc(cr4, 3,1, "DE")            # debugging extensions
    PSE = slc(cr4, 4,1, "PSE")           # page size extensions
    PAE = slc(cr4, 5,1, "PAE")           # physical address extension
    MCE = slc(cr4, 6,1, "MCE")           # machine check enable
    PGE = slc(cr4, 7,1, "PGE")           # page global enable
    PCE = slc(cr4, 8,1, "PCE")           # perf monitor counter enable
    OSFXSR = slc(cr4, 9,1, "OSFXSR")         # OS FXSAVE/FXRSTOR support
    OSXMMEXCPT = slc(cr4,10,1, "OSXMMEXCPT") # OS unmasked exception support
    UMIP = slc(cr4,11,1, "UMIP")         # usermode instruction prevention
    LA57 = slc(cr4,12,1, "LA57")         # 5-level paging enable
    FSGSBASE = slc(cr4,16,1, "FSGSBASE") # enable xxxBASE instructions
    PCIDE = slc(cr4,17,1, "PCIDE")       # process context identifier enable
    OSXSAVE = slc(cr4,18,1, "OSXSAVE")   # XSAVE and processor extended states enable
    SMEP = slc(cr4,20,1, "SMEP")         # supervisor mode execution protection
    SMAP = slc(cr4,21,1, "SMAP")         # supervisor mode access protection
    PKE = slc(cr4,22,1, "PKE")           # protection key enable
    CET = slc(cr4,23,1, "CET")           # control-flow enforcement technology

    EFER  = reg("EFER",32)
    SCE   = slc(EFER, 0,1,"SCE")    # system call extensions
    LME   = slc(EFER, 8,1,"LME")    # long mode enable
    LMA   = slc(EFER,10,1,"LMA")    # long mode active
    NXE   = slc(EFER,11,1,"NXE")    # non-executable enable
    SVME  = slc(EFER,12,1,"SVME")   # secure virtual machine enable
    LMSLE = slc(EFER,13,1,"LMSLE")  # long mode segment limit enable
    FFXSR = slc(EFER,14,1,"FFXSR")  # fast FXSAVE/FXRSTOR
    TCE   = slc(EFER,15,1,"TCE")    # translation cache extension

    dr0 = reg("dr0", 32)
    dr1 = reg("dr1", 32)
    dr2 = reg("dr2", 32)
    dr3 = reg("dr3", 32)
    dr6 = reg("dr6", 32)
    dr7 = reg("dr7", 32)

    # Global/Interrupt/Local Descriptors Tables:
    GDTR = reg("GDTR",48)
    IDTR = reg("IDTR",48)

    # LDT and task register (segment selector):
    LDTR = reg("LDTR",16)
    TR   = reg("TR",16)

def cr(num):
    return [cr0,None,cr2,cr3,cr4,None,None,None,cr8][num]
def dr(num):
    return [dr0,dr1,dr2,dr3,None,None,dr6,dr7][num]




internals = {"mode": 32, "ring": 3, "seg":False}

registers = [eax,ecx,edx,ebx,esp,ebp,esi,edi,eip,eflags,cs,ss,ds,es,fs,gs]
