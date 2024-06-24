# -*- coding: utf-8 -*-

from amoco.arch.z80 import env
from amoco.arch.z80 import asm

# import specifications:
from amoco.arch.core import instruction, disassembler, CPU

instruction_gb = type("instruction_gb", (instruction,), {})

from amoco.arch.z80.formats import GB_full

instruction_gb.set_formatter(GB_full)

# define disassembler:
from amoco.arch.z80 import spec_gb

disassemble = disassembler([spec_gb], iclass=instruction_gb)

cpu = CPU(env, asm, disassemble, env.pc)
