from amoco.system.baremetal.imx6 import HAB_Header, HAB_TAG_IVT


def test_header():
    h = HAB_Header(b"\xd1\x00\x20\x40")
    assert h.tag == HAB_TAG_IVT
    assert h.tag == 0xD1
    assert h.length == 32
    assert h.version == 0x40
