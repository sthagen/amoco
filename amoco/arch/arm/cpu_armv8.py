# -*- coding: utf-8 -*-

# This code is part of Amoco
# Copyright (C) 2006-2014 Axel Tillequin (bdcht3@gmail.com)
# published under GPLv2 license

from amoco.arch.arm.v8 import env64 as env
from amoco.arch.arm.v8 import asm64
from amoco.arch.core import instruction, disassembler, CPU

# define disassembler:
from amoco.arch.arm.v8 import spec_armv8
from amoco.arch.arm.v8.formats import ARM_V8_full

instruction_armv8 = type("instruction_armv8", (instruction,), {})
instruction_armv8.set_formatter(ARM_V8_full)


def endian():
    return 1 if env.internals["ibigend"] == 0 else -1


disassemble = disassembler([spec_armv8], endian=endian, iclass=instruction_armv8)


class CPU_ARMv8(CPU):
    def get_data_endian(self):
        return 1 if env.internals["endianstate"] == 0 else -1


cpu = CPU_ARMv8(env, asm64, disassemble, env.pc)
