# -*- coding: utf-8 -*-

from amoco.arch.ppc32.e200 import env
from amoco.arch.ppc32.e200 import asm

# import specifications:
from amoco.arch.core import instruction, disassembler, CPU

instruction_e200 = type("instruction_e200", (instruction,), {})

from amoco.arch.ppc32.e200.formats import PPC_full

instruction_e200.set_formatter(PPC_full)

# define disassembler:
from amoco.arch.ppc32.e200 import spec_vle


def endian():
    return -1


disassemble = disassembler([spec_vle], iclass=instruction_e200, endian=endian)

cpu = CPU(env, asm, disassemble, env.pc, data_endian=-1)
