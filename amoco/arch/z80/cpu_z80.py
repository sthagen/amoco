# -*- coding: utf-8 -*-

from amoco.arch.z80 import env
from amoco.arch.z80 import asm

# import specifications:
from amoco.arch.core import instruction, disassembler, CPU

instruction_z80 = type("instruction_z80", (instruction,), {})

from amoco.arch.z80.formats import Mostek_full

instruction_z80.set_formatter(Mostek_full)

# define disassembler:
from amoco.arch.z80 import spec_mostek

disassemble = disassembler([spec_mostek], iclass=instruction_z80)

cpu = CPU(env, asm, disassemble, env.pc)
