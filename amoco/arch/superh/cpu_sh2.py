# -*- coding: utf-8 -*-

from amoco.arch.superh.sh2 import env
from amoco.arch.superh.sh2 import asm

# import specifications:
from amoco.arch.core import instruction, disassembler, CPU

instruction_sh2 = type("instruction_sh2", (instruction,), {})

from amoco.arch.superh.sh2.formats import SH2_full

instruction_sh2.set_formatter(SH2_full)

# define disassembler:
from amoco.arch.superh.sh2 import spec_sh2


def endian():
    return -1


disassemble = disassembler([spec_sh2], endian=endian, iclass=instruction_sh2)

cpu = CPU(env, asm, disassemble, env.pc)
