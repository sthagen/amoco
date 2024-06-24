# -*- coding: utf-8 -*-

from amoco.arch.eBPF import env
from amoco.arch.eBPF import asm

# import specifications:
from amoco.arch.core import instruction, disassembler, CPU

from amoco.arch.eBPF.formats import eBPF_full

# define disassembler:
from amoco.arch.eBPF import spec

instruction_eBPF = type("instruction_eBPF", (instruction,), {})
instruction_eBPF.set_formatter(eBPF_full)

disassemble = disassembler([spec], iclass=instruction_eBPF)

cpu = CPU(env, asm, disassemble, env.pc)
cpu.registers = env.R + [env.pc]
