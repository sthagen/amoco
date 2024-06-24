# -*- coding: utf-8 -*-

from amoco.arch.sparc import env
from amoco.arch.sparc import asm

# import specifications:
from amoco.arch.core import instruction, disassembler, CPU

instruction_sparc = type("instruction_sparc", (instruction,), {})

from amoco.arch.sparc.formats import SPARC_V8_synthetic

instruction_sparc.set_formatter(SPARC_V8_synthetic)

# define disassembler:
from amoco.arch.sparc import spec_v8


def endian():
    return -1


disassemble = disassembler([spec_v8], endian=endian, iclass=instruction_sparc)

cpu = CPU(env, asm, disassemble, env.pc, data_endian=-1)
