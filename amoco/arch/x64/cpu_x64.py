# -*- coding: utf-8 -*-

from amoco.arch.x64 import env
from amoco.arch.x64 import asm

from amoco.arch.core import instruction, disassembler, CPU

instruction_x64 = type("instruction_x64", (instruction,), {})
from amoco.arch.x64.formats import IA32e_Intel, IA32e_ATT

instruction_x64.set_formatter(IA32e_Intel)

from amoco.arch.x64 import spec_ia32e

disassemble = disassembler([spec_ia32e], iclass=instruction_x64)
disassemble.maxlen = 15


class CPU_ia32e(CPU):
    def getPC(self, state=None):
        return env.rip if state is None else state(env.ptr(env.rip, seg=env.cs))

    def push(self, m, x):
        asm.push(m, x)

    def pop(self, m, x):
        asm.pop(m, x)


cpu = CPU_ia32e(env, asm, disassemble)


def configure(**kargs):
    from amoco.config import conf

    # asm format:
    f = kargs.get("format", conf.Arch.format_x64)
    if f in ("AT&T", "at&t", "ATT", "att"):
        instruction_x64.set_formatter(IA32e_ATT)
    elif f in ("Intel", "INTEL", "intel"):
        instruction_x64.set_formatter(IA32e_Intel)


configure()
