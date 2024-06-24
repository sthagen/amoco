import amoco


def test_loader_001(samples):
    for f in samples:
        p = amoco.read_program(f)
        assert p is not None


def test_loader_002(samples):
    for f in samples:
        p = amoco.load_program(f)
        assert p is not None


def test_loader_003(sc1):
    p = amoco.load_program(sc1)
    assert p.bin.dataio.f.getvalue() == sc1
    assert p.bin.filename == "(sc-eb165e31...)"
