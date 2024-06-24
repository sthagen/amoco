# -*- coding: utf-8 -*-

from amoco.arch.mips.r3000 import env
from amoco.arch.mips.r3000 import asm

# import specifications:
from amoco.arch.core import instruction, disassembler, CPU

instruction_r3000 = type("instruction_r3000", (instruction,), {})

from amoco.arch.mips.r3000.formats import MIPS_full

instruction_r3000.set_formatter(MIPS_full)

# define disassembler:
from amoco.arch.mips.r3000 import spec


def endian():
    return -1


disassemble = disassembler([spec], iclass=instruction_r3000, endian=endian)

cpu = CPU(env, asm, disassemble, pc_expr=env.pc, data_endian=-1)
