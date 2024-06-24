# -*- coding: utf-8 -*-

from amoco.arch.w65c02 import env
from amoco.arch.w65c02 import asm

# import specifications:
from amoco.arch.core import instruction, disassembler, CPU

instruction_w65c02 = type("instruction_w65c02", (instruction,), {})

from amoco.arch.w65c02.formats import w65c02_full

instruction_w65c02.set_formatter(w65c02_full)

# define disassembler:
from amoco.arch.w65c02 import spec

disassemble = disassembler([spec], iclass=instruction_w65c02)

cpu = CPU(env, asm, disassemble, env.pc)
