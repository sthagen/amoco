# -*- coding: utf-8 -*-

from amoco.arch.msp430 import env
from amoco.arch.msp430 import asm

# import specifications:
from amoco.arch.core import instruction, disassembler, CPU

instruction_msp430 = type("instruction_msp430", (instruction,), {})

from amoco.arch.msp430.formats import MSP430_synthetic

instruction_msp430.set_formatter(MSP430_synthetic)

# define disassembler:
from amoco.arch.msp430 import spec_msp430

disassemble = disassembler([spec_msp430], iclass=instruction_msp430)
disassemble.maxlen = 6

cpu = CPU(env, asm, disassemble, env.pc)
