# -*- coding: utf-8 -*-

from amoco.arch.avr import env
from amoco.arch.avr import asm

# import specifications:
from amoco.arch.core import instruction, disassembler, CPU

# define disassembler:
from amoco.arch.avr import spec

from amoco.arch.avr.formats import AVR_full

instruction_avr = type("instruction_avr", (instruction,), {})
instruction_avr.set_formatter(AVR_full)

disassemble = disassembler([spec], iclass=instruction_avr)

cpu = CPU(env, asm, disassemble, env.pc)
