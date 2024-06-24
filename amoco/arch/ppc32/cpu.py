# -*- coding: utf-8 -*-

from amoco.arch.ppc32 import env
from amoco.arch.ppc32 import asm

# import specifications:
from amoco.arch.core import instruction, disassembler, CPU

instruction_ppc32 = type("instruction_ppc32", (instruction,), {})

from amoco.arch.ppc32.formats import PPC_full

instruction_ppc32.set_formatter(PPC_full)

# define disassembler:
from amoco.arch.ppc32 import spec_booke as spec


def endian():
    return -1


disassemble = disassembler([spec], iclass=instruction_ppc32, endian=endian)

cpu = CPU(env, asm, disassemble, env.pc, data_endian=-1)
