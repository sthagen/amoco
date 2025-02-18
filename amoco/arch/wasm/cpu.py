# -*- coding: utf-8 -*-

from amoco.arch.wasm import env
from amoco.arch.wasm import asm

# import specifications:
from amoco.arch.core import instruction, disassembler, CPU

instruction_wasm = type("instruction_wasm", (instruction,), {})

from amoco.arch.wasm.formats import DW_full

instruction_wasm.set_formatter(DW_full)

# define disassembler:
from amoco.arch.wasm import spec

disassemble = disassembler([spec], iclass=instruction_wasm)

# wasm instructions are fully determined with 1 byte only, but the operands
# are encoded in leb128 form for 32 or 33 bits integers. Wasm enforces a leb128
# encoding of ceil(N/7), leading to at most 5 bytes for one leb128 value.
# Since most instructions have not more than 3 operands we set the maxlen to 16.
# If an instruction needs more bytes in must rely on the xdata API (see arch.core.)
disassemble.maxlen = 16

cpu = CPU(env, asm, disassemble, env.op_ptr)
