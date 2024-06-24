# -*- coding: utf-8 -*-

from amoco.arch.superh.sh4 import env
from amoco.arch.superh.sh4 import asm

# import specifications:
from amoco.arch.core import instruction, disassembler, CPU

instruction_sh4 = type("instruction_sh4", (instruction,), {})

from amoco.arch.superh.sh4.formats import SH4_synthetic

instruction_sh4.set_formatter(SH4_synthetic)

# define disassembler:
from amoco.arch.superh.sh4 import spec_sh4


def endian():
    return -1


disassemble = disassembler([spec_sh4], endian=endian, iclass=instruction_sh4)

cpu = CPU(env, asm, disassemble, env.pc)
