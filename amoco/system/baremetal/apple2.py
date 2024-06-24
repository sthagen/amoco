# -*- coding: utf-8 -*-

# This code is part of Amoco
# Copyright (C) 2021 Axel Tillequin (bdcht3@gmail.com)
# published under GPLv2 license

from amoco.system.core import shellcode, DataIO, CoreExec, DefineStub
from amoco.arch.w65c02.cpu import cpu
from amoco.logger import Log

logger = Log(__name__)
logger.debug("loading module")

IRQV = 0xFFFE
RESETV = 0xFFFC
SOFTEV = 0x03F2
PWREDUP = 0x03F4

IOMAP = [
    ("IO_KBD/80STOREOFF", 0xC000),
    ("80STOREON", 0xC001),
    ("RAMRDOFF", 0xC002),
    ("RAMRDON", 0xC003),
    ("RAMWRTOFF", 0xC004),
    ("RAMWRTON", 0xC005),
    ("ALTZPOFF", 0xC008),
    ("ALTZPON", 0xC009),
    ("80COLOFF", 0xC00C),
    ("80COLON", 0xC00D),
    ("ALTCHARSETOFF", 0xC00E),
    ("ALTCHARSETON", 0xC00F),
    ("KBDSTRB", 0xC010),
    ("RDBANK2", 0xC011),
    ("RDLCRAM", 0xC012),
    ("RAMRD", 0xC013),
    ("RAMWRT", 0xC014),
    ("MOUSEXINT", 0xC015),
    ("ALTZP", 0xC016),
    ("MOUSEYINT", 0xC017),
    ("80STORE", 0xC018),
    ("VBLINT", 0xC019),
    ("TEXT", 0xC01A),
    ("MIXED", 0xC01B),
    ("PAGE2", 0xC01C),
    ("HIRES", 0xC01D),
    ("ALTCHARSET", 0xC01E),
    ("80COL", 0xC01F),
    *[("SPEAKER", 0xC030 + i) for i in range(16)],
    ("RDXYMSK", 0xC040),
    ("RDVBLMSK", 0xC041),
    ("RDX0EDGE", 0xC042),
    ("RDY0EDGE", 0xC043),
    ("RSTXY", 0xC048),
    ("TEXTOFF", 0xC050),
    ("TEXTON", 0xC051),
    ("MIXEDOFF", 0xC052),
    ("MIXEDON", 0xC053),
    ("PAGE2OFF", 0xC054),
    ("PAGE2ON", 0xC055),
    ("HIRESOFF", 0xC056),
    ("HIRESON", 0xC057),
    ("DISXY", 0xC058),
    ("ENBXY", 0xC059),
    ("DISVBL", 0xC05A),
    ("ENVBL", 0xC05B),
    ("RX0EDGE", 0xC05C),
    ("FX0EDGE", 0xC05D),
    ("RY0EDGE", 0xC05E),
    ("FY0EDGE", 0xC05F),
    ("RD80SW", 0xC060),
    ("PB0", 0xC061),
    ("PB1", 0xC062),
    ("RD63", 0xC063),
    ("PDL0", 0xC064),
    ("PDL1", 0xC065),
    ("MOUX1", 0xC066),
    ("MOUY1", 0xC067),
    ("PTRIG", 0xC070),
    *[("RDIOUDIS", i) for i in (0xC078, 0xC07A, 0xC07C, 0xC07E)],
    *[("DHIRES", i) for i in (0xC079, 0xC07B, 0xC07D, 0xC07F)],
    ("READBSR2", 0xC080),
    ("WRITEBSR2", 0xC081),
    ("OFFBSR2", 0xC082),
    ("RDWRBSR2", 0xC083),
    ("READBSR1", 0xC088),
    ("WRITEBSR1", 0xC089),
    ("OFFBSR1", 0xC08A),
    ("RDWRBSR1", 0xC08B),
    ("DATAREG1", 0xC098),
    ("STATUS1", 0xC099),
    ("COMMAND1", 0xC09A),
    ("CONTROL1", 0xC09B),
    ("DATAREG2", 0xC0A8),
    ("STATUS2", 0xC0A9),
    ("COMMAND2", 0xC0AA),
    ("CONTROL2", 0xC0AB),
]

# ----------------------------------------------------------------------------


class AppleROM(CoreExec):
    def __init__(self, romfile, cpu):
        try:
            f = open(romfile, "rb")
        except (ValueError, TypeError, IOError):
            print("romfile '%s' not found" % romfile)
        else:
            rom = DataIO(f)
            super().__init__(shellcode(rom), cpu)
            # setup memory space:
            # -------------------
            # [0x0000-0x00FF] zero page:
            self.state.mmap.write(0, b"\0" * 0x100)
            # [0x0100-0x01FF] stack:
            self.state.mmap.write(0x100, b"\0" * 0x100)
            # [0x0200-0x02FF] input buffer (keyboard/floppy):
            self.state.mmap.write(0x200, b"\0" * 0x100)
            # [0x0300-0x03FF] program space & system API:
            self.state.mmap.write(0x300, b"\0" * 0x100)
            # [0x0400-0x07FF] video page1:
            self.state.mmap.write(0x400, b"\0" * 0x400)
            # [0x0800-0x0BFF] video page2:
            self.state.mmap.write(0x800, b"\0" * 0x400)
            # [0x0C00-0x1FFF] is free...
            # [0x2000-0x3FFF] high-res video page1:
            self.state.mmap.write(0x2000, b"\0" * 0x2000)
            # [0x4000-0x5FFF] high-res video page2:
            self.state.mmap.write(0x4000, b"\0" * 0x2000)
            # [0x6000-0xBFFF] is free...
            # [0xC000-0xC0FF] memory-mapped I/O:
            for io, addr in IOMAP:
                xf = cpu.ext(io, size=8)
                xf.stub = Apple2c.stubs.get(xf.ref)
                self.state.mmap.write(addr, xf)
            # [0xC100-0xFFFF] ROM memory:
            self.setup_rom()

    def setup_rom(self):
        # C100-CFFF contains extensions to the system monitor, and subroutines
        # to support 80-column text displau, printer, modem, mouse and disk.
        self.state.mmap.write(0x10000 - self.bin.data.size(), self.bin.data[0:])
        # D000-F7FF contains the Applesoft ROM
        # F800-FFFF contains the system monitor ROM


# ----------------------------------------------------------------------------


class Apple2c(object):
    stubs = {}
    default_stub = DefineStub.warning

    def __init__(self, conf=None):
        if conf is None:
            from amoco.config import System

            conf = System()
        self.romfile = conf.romfile
        self.tasks = []
        self.abi = None
        self.symbols = {}

    @classmethod
    def loader(cls, bprm, conf=None):
        return cls(conf).load_bin(bprm)

    def load_bin(self, bprm):
        p = AppleROM(self.romfile, cpu)
        p.OS = self
        # define registers:
        p.state[cpu.sp_] = cpu.cst(0x1FF, 16)
        p.state[cpu.A] = cpu.cst(0xFF, 8)
        p.state[cpu.X] = cpu.cst(0xFF, 8)
        p.state[cpu.Y] = cpu.cst(0xFF, 8)
        p.state[cpu.P] = cpu.cst(0xFF, 8)
        p.state[cpu.D] = cpu.bit0
        entry = p.state(cpu.mem(cpu.RESETV, 16))
        p.state[cpu.pc] = entry
        # map the stack area:
        p.state.mmap.write(0x100, b"\0" * 0x100)
        self.tasks.append(p)
        return p

    @classmethod
    def stub(cls, refname):
        return cls.stubs.get(refname, cls.default_stub)


# ----------------------------------------------------------------------------


@DefineStub(Apple2c, "IO_KBD/80STOREOFF")
def io_kbd_80storeoff(m, mode):
    m[cpu.pc] = m(cpu.mem(cpu.sp_, 16))
    m[cpu.sp] = m(cpu.sp + 2)
