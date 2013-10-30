import unittest

import pycbor


class TestEncode(unittest.TestCase):
    def test_array(self):
        array = [1, [2, 3], [4, 5]]
        self.assertEqual(pycbor.encode(array), b'\x83\x01\x82\x02\x03\x82\x04\x05')

    def test_array_indefinite(self):
        array = [1, [2, 3], range(4, 6)]
        self.assertEqual(pycbor.encode(array), b'\x83\x01\x82\x02\x03\x9f\x04\x05\xff')

    def test_unsigned(self):
        self.assertEqual(pycbor.encode(500), b'\x19\x01\xf4')

    def test_signed(self):
        self.assertEqual(pycbor.encode(-500), b'\x39\x01\xf3')
