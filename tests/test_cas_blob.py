from amoco.cas.blobs import blob, blob_ptr, blob_comp, uint8, uint16, uint32
from amoco.cas.expressions import cst, ptr, reg, mem, bit0, bit1
from amoco.cas.mapper import mapper


def test_blob_core():
    b = blob(uint8, a=ptr(reg("a", 32)), raw=b"\x01\x02\x03\x04")
    assert b._is_cst
    assert b.size == 8
    assert b.length == 1
    assert hasattr(b, "etype")
    assert b.bytes(1, 3) == b"\x02\x03"


def test_blob_ptr_1():
    a = reg("a", 32)
    b = blob_ptr(uint16, a=ptr(a, disp=8))
    assert b._is_mem
    env = mapper()
    env[reg("df", 1)] = bit0  # just to have a non empty mapper
    env.mmap.write(ptr(a, disp=4), b"XXXX" + (b"A" * 40) + b"YYYY")
    x = env(b.as_array(20, d=0))
    assert isinstance(x, blob)
    assert x._is_cst
    assert x.length == 40
    assert x.raw == b"A" * 40


def test_blob_ptr_2():
    a = reg("a", 32)
    b = blob_ptr(uint32, a=ptr(a, disp=256))
    assert b._is_mem
    env = mapper()
    env[reg("df", 1)] = df = bit1  # just to have a non empty mapper
    env.mmap.write(ptr(a), b"B" * 256 + b"ZZZZ")
    x = env(b.as_array(64, df))
    assert isinstance(x, blob)
    assert x._is_cst
    assert len(x) == x.length == 256
    assert x.raw == b"B" * 256
    assert len(x.val) == 64
    assert x.val[0] == 0x42424242
    env[ptr(reg("b", 32), disp=256)] = x
    assert env.mmap.read(ptr(reg("b", 32)), 256)[0] == x.raw


def test_blob_infinite():
    # an infinite blob is produced when its size is symbolic (not a cst).
    a = reg("a", 32)
    b = blob_ptr(uint8, a=ptr(a, disp=0x1000))
    assert b._is_mem
    env = mapper()
    env[reg("df", 1)] = bit0  # just to have a non empty mapper
    env.mmap.write(ptr(a, disp=0x1004), b"XXXX" + (b"A" * 40) + b"YYYY")
    # array size is undefined:
    x = env(b.as_array(reg("cx", 16)))
    assert isinstance(x, blob)
    assert x._is_mem
    assert x.length == float("Infinity")
    env.mmap.write(ptr(a), x)
    v = env(mem(ptr(a), disp=4, size=32))
    assert v._is_mem
    assert v.size == 32
    assert v.a.disp == 0x1004


def test_blob_symbolic():
    # a symbolic blob is produced when symbolic data exists at given address
    a = reg("a", 32)
    b = blob_ptr(uint8, a=ptr(a, disp=0x1000))
    assert b._is_mem
    env = mapper()
    env[reg("df", 1)] = bit0  # just to have a non empty mapper
    env.mmap.write(ptr(a, disp=0x1004), b"XXXX" + (b"A" * 40) + b"YYYY")
    env[ptr(a, disp=0x1000)] = mem(ptr(reg("b", 32)), 32)
    # array size is undefined:
    x = env(b.as_array(20))
    assert isinstance(x, blob)
    assert x._is_mem
    assert x.length == 20
    env.mmap.write(ptr(cst(0x100, 32)), x)
    v = env(mem(cst(0x100, 32), size=32))
    assert v._is_mem
    assert v.size == 32
    assert v.a.disp == 0x1000


def test_blob_comp_1():
    src = blob_comp(dt=4, el=cst(0, 32)).as_array(100, d=1)
    assert src._is_cst
    assert src.length == 400
    assert len(src.val) == 100
    assert src.data._is_cst
    assert src.data.size == 3200
    assert src.bytes(13, 17) == b"\x00\x00\x00\x00"
    env = mapper()
    env[reg("df", 1)] = bit1  # just to have a non empty mapper
    env[ptr(cst(0x1000, 32))] = src
    assert env.mmap.read(0xF00, 4) == [b"\x00\x00\x00\x00"]


def test_blob_comp_2():
    src = blob_comp(dt=4, el=reg("a", 32)).as_array(100)
    assert src._is_cmp
    assert src.length == 400
    assert len(src.data) == 400
    assert src.data._is_cmp
    assert src.data.size == 3200
    assert src.bytes(13, 17)[24:32] == reg("a", 32)[0:8]
    env = mapper()
    env[reg("df", 1)] = bit0  # just to have a non empty mapper
    dst = ptr(reg("b", 32))
    env[dst] = src
    y = env(mem(dst, disp=13, size=32))
    assert y._is_cmp
    assert y == src.bytes(13, 17)
