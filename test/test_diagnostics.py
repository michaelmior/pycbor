import pycbor


def test_encode(diagnostic, encoded):
    assert encoded == pycbor.encode(diagnostic)


def test_decode(encoded, diagnostic):
    assert pycbor.decode(encoded) == diagnostic
