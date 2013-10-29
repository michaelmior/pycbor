import collections
import struct


def _encode_int(data, major_type):
    encoded = b''

    if 0 <= data <= 23:
        encoded += bytes([(major_type << 5) + data])
    elif data < (2 << 7) - 1:
        encoded += bytes([(major_type << 5) + 24])
        encoded += struct.pack('>B', data)
    elif data < (2 << 15) - 1:
        encoded += bytes([(major_type << 5) + 25])
        encoded += struct.pack('>H', data)
    elif data < (2 << 31) - 1:
        encoded += bytes([(major_type << 5) + 26])
        encoded += struct.pack('>I', data)
    elif data < (2 << 63) - 1:
        encoded += bytes([(major_type << 5) + 27])
        encoded += struct.pack('>Q', data)

    return encoded

def encode(data):
    encoded = b''

    if isinstance(data, list) or isinstance(data, tuple):
        encoded += _encode_int(len(data), 4)
        for item in data:
            encoded += encode(item)
        return encoded

    if isinstance(data, dict):
        encoded += _encode_int(len(data), 5)
        for key, value in data.items():
            encoded += encode(key)
            encoded += encode(value)
        return encoded

    simple = {
        False: 20,
        True: 21,
        None: 22,
    }

    if data is True or data is False or data is None:
        encoded += bytes([(7 << 5) + simple[data]])
        return encoded

    if isinstance(data, int):
        if data < 0:
            data = -1 - data
            major_type = 1
        else:
            major_type = 0

        encoded += _encode_int(data, major_type)
        return encoded

    if isinstance(data, bytes):
        encoded += _encode_int(len(data), 2)
        encoded += data
        return encoded

    if isinstance(data, str):
        encoded += _encode_int(len(data), 3)
        encoded += data.encode('utf8')
        return encoded

    if isinstance(data, collections.Iterable):
        encoded += bytes([(4 << 5) + 31])
        for item in data:
            encoded += encode(item)
        encoded += b'\xff'
        return encoded

    if isinstance(data, float):
        encoded += bytes([(7 << 5) + 27])
        encoded += struct.pack('>d', data)
        return encoded


def decode(data):
    pass
