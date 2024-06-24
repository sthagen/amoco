# -*- coding: utf-8 -*-

from amoco.arch.eBPF import env
from amoco.arch.eBPF import asm

# import specifications:
from amoco.arch.core import instruction, disassembler, CPU

# we use the same formatter has eBPF...
from amoco.arch.eBPF.formats import eBPF_full

# define disassembler with spec_bpf module:
from amoco.arch.eBPF import spec_bpf

instruction_BPF = type("instruction_BPF", (instruction,), {})
instruction_BPF.set_formatter(eBPF_full)

disassemble = disassembler([spec_bpf], iclass=instruction_BPF)

cpu = CPU(env, asm, disassemble, env.pc)
cpu.registers = [env.A, env.X] + env.M + [env.pc]
