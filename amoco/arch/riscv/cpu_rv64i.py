# -*- coding: utf-8 -*-

from amoco.arch.riscv.rv64i import env
from amoco.arch.riscv.rv64i import asm

# import specifications:
from amoco.arch.core import instruction, disassembler, CPU

instruction_riscv64 = type("instruction_riscv64", (instruction,), {})

from amoco.arch.riscv.rv64i.formats import RISCV_full

instruction_riscv64.set_formatter(RISCV_full)

# define disassembler:
from amoco.arch.riscv.rv64i import spec_rv64i

disassemble = disassembler([spec_rv64i], iclass=instruction_riscv64)

cpu = CPU(env, asm, disassemble, env.pc)
