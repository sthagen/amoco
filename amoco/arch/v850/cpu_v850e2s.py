# -*- coding: utf-8 -*-

from amoco.arch.v850 import env
from amoco.arch.v850 import asm

# import specifications:
from amoco.arch.core import instruction, disassembler, CPU

instruction_v850 = type("instruction_v850", (instruction,), {})

from amoco.arch.v850.formats import v850_full

instruction_v850.set_formatter(v850_full)

# define disassembler:
import amoco.arch.v850.spec_v850e2s as spec

disassemble = disassembler([spec], iclass=instruction_v850)

cpu = CPU(env, asm, disassemble, env.pc)
