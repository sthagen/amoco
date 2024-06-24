# -*- coding: utf-8 -*-

from amoco.arch.tricore import env
from amoco.arch.tricore import asm

# import specifications:
from amoco.arch.core import instruction, disassembler, CPU

instruction_tricore = type("instruction_tricore", (instruction,), {})

from amoco.arch.tricore.formats import TriCore_full

instruction_tricore.set_formatter(TriCore_full)

# define disassembler:
from amoco.arch.tricore import spec

disassemble = disassembler([spec], iclass=instruction_tricore)

cpu = CPU(env, asm, disassemble, env.pc)
