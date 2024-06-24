# -*- coding: utf-8 -*-

from amoco.arch.riscv.rv32i import env
from amoco.arch.riscv.rv32i import asm

# import specifications:
from amoco.arch.core import instruction, disassembler, CPU

instruction_riscv = type("instruction_riscv", (instruction,), {})

from amoco.arch.riscv.rv32i.formats import RISCV_full

instruction_riscv.set_formatter(RISCV_full)

# define disassembler:
from amoco.arch.riscv.rv32i import spec_rv32i

disassemble = disassembler([spec_rv32i], iclass=instruction_riscv)

cpu = CPU(env, asm, disassemble, env.pc)
