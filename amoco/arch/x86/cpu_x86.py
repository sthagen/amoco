# -*- coding: utf-8 -*-
from amoco.arch.x86 import env
from amoco.arch.x86 import asm
from amoco.arch.x86 import hw

from amoco.arch.core import instruction, disassembler, CPU

instruction_x86 = type("instruction_x86", (instruction,), {})

from amoco.arch.x86.formats import IA32_ATT, IA32_Intel

instruction_x86.set_formatter(IA32_Intel)

from amoco.arch.x86 import spec_ia32

disassemble = disassembler([spec_ia32], iclass=instruction_x86)
disassemble.maxlen = 15


class CPU_ia32(CPU):
    def getPC(self, state=None):
        return env.eip if state is None else state(env.ptr(env.eip, seg=env.cs))

    def push(self, m, x):
        return asm.push(m, x)

    def pop(self, m, x):
        return asm.pop(m, x)


cpu = CPU_ia32(env, asm, disassemble)
cpu.hw = hw


def configure(**kargs):
    from amoco.config import conf

    # asm format:
    f = kargs.get("format", conf.Arch.format_x86)
    if f in ("AT&T", "at&t", "ATT", "att"):
        instruction_x86.set_formatter(IA32_ATT)
    elif f in ("Intel", "INTEL", "intel"):
        instruction_x86.set_formatter(IA32_Intel)


configure()
