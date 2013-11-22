import pycbor
import math

def test_encode(diagnostic, encoded):
    if isinstance(diagnostic, float):
        if not math.isfinite(diagnostic) and len(encoded) > 3:
            return
    if (isinstance(diagnostic, list) or isinstance(diagnostic, dict)) and 0xff in encoded:
        return
    if (isinstance(diagnostic, tuple)):
        return
    assert encoded == pycbor.encode(diagnostic)


def test_decode(encoded, diagnostic):
    if isinstance(diagnostic, float) and math.isnan(diagnostic):
        assert math.isnan(pycbor.decode(encoded))
        return
    if isinstance(diagnostic, tuple):
        diagnostic = ''.join(str(elem) for elem in diagnostic)
    assert pycbor.decode(encoded) == diagnostic
