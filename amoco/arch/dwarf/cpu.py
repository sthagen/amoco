# -*- coding: utf-8 -*-

from amoco.arch.dwarf import env
from amoco.arch.dwarf import asm

# import specifications:
from amoco.arch.core import instruction, disassembler, CPU
from amoco.arch.dwarf.formats import DW_full

# define disassembler:
from amoco.arch.dwarf import spec

instruction_dwarf = type("instruction_dwarf", (instruction,), {})
instruction_dwarf.set_formatter(DW_full)

disassemble = disassembler([spec], iclass=instruction_dwarf)
disassemble.maxlen = 21

cpu = CPU(env, asm, disassemble, env.op_ptr)
