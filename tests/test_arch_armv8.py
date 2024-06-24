from amoco.arch.arm.cpu_armv8 import cpu

from amoco.ui import render

render.conf.UI.formatter = "Null"


def test_decoder_000():
    c = b"\x67\x0a\x00\xd0"
    i = cpu.disassemble(c)
    assert i.mnemonic == "ADRP"
    assert i.operands[0] == cpu.r7
    assert i.operands[1] == 0x14E000


def test_decoder_001():
    c = b"\xe1\x17\x9f\x1a"
    i = cpu.disassemble(c)
    assert i.mnemonic == "CSINC"
    assert i.operands[0] == cpu.w1
    assert cpu.CONDITION[i.cond ^ 1][0] == "eq"


def test_decoder_003():
    c = b"\xe5\x54\x42\xb8"
    i = cpu.disassemble(c)
    assert i.mnemonic == "LDR"
    assert i.operands[0] == cpu.w5
    assert i.operands[1] == cpu.r7
    assert i.operands[2] == 0x25


# SIMD:


def test_decoder_004():
    c = b"\xe5\x54\x42\xfd"
    i = cpu.disassemble(c)
    assert i is not None
    assert i.scale==3
    assert i.t.ref=='V5'
    assert i.n.ref=='X7'


def test_decoder_005():
    c = b"\xe5\x54\x42\xbd"
    i = cpu.disassemble(c)
    assert i is not None
    assert i.scale==2
    assert i.t.ref=='V5'
    assert i.n.ref=='X7'
    assert i.operands[-1] == 596


# ------------------------------------------------------------------------------


def test_asm_000(amap):
    c = b"\x67\x0a\x00\xd0"
    i = cpu.disassemble(c)
    # fake eip cst:
    amap[cpu.pc] = cpu.cst(0x400924, 64)
    i(amap)
    assert amap(cpu.r7) == 0x54E000
