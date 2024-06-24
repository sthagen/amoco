# -*- coding: utf-8 -*-

# This code is part of Amoco
# Copyright (C) 2006-2014 Axel Tillequin (bdcht3@gmail.com)
# published under GPLv2 license

from amoco.arch.arm.v7 import env
from amoco.arch.arm.v7 import asm
from amoco.arch.core import instruction, disassembler, CPU

# define disassembler:
from amoco.arch.arm.v7 import spec_armv7
from amoco.arch.arm.v7 import spec_thumb

from amoco.arch.arm.v7.formats import ARM_V7_full

instruction_armv7 = type("instruction_armv7", (instruction,), {})
instruction_armv7.set_formatter(ARM_V7_full)


def mode(**kargs):
    return env.internals["isetstate"]


def endian(**kargs):
    return 1 if env.internals["ibigend"] == 0 else -1


disassemble = disassembler([spec_armv7, spec_thumb], instruction_armv7, mode, endian)


class CPU_ARMv7(CPU):
    def get_data_endian(self):
        return 1 if env.internals["endianstate"] == 0 else -1


cpu = CPU_ARMv7(env, asm, disassemble, env.pc_)
