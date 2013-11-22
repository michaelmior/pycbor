import pycbor
import math

def test_encode(diagnostic, encoded):
    if isinstance(diagnostic, float):
        if not math.isfinite(diagnostic) and len(encoded) > 3:
            return
    assert encoded == pycbor.encode(diagnostic)


def test_decode(encoded, diagnostic):
    if isinstance(diagnostic, float) and math.isnan(diagnostic):
        assert math.isnan(pycbor.decode(encoded))
        return
    assert pycbor.decode(encoded) == diagnostic
