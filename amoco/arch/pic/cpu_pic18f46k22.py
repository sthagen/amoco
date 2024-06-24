# -*- coding: utf-8 -*-

from amoco.arch.pic.F46K22 import env
from amoco.arch.pic.F46K22 import asm

# import specifications:
from amoco.arch.core import instruction, disassembler, CPU

instruction_f46k22 = type("instruction_f46k22", (instruction,), {})

from amoco.arch.pic.F46K22.formats import PIC_full

instruction_f46k22.set_formatter(PIC_full)

# define disassembler:
from amoco.arch.pic.F46K22 import spec_pic18

disassemble = disassembler([spec_pic18], iclass=instruction_f46k22)

cpu = CPU(env, asm, disassemble, env.pc)
