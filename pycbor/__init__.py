import collections
import struct
import math
import array

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
    else:
        # TODO Handle values in this range
        raise ValueError

    return encoded


def _single_to_half(single):
    f = struct.unpack(">I", struct.pack(">f", single))[0]
    h = ((f >> 16) & 0x8000) | ((((f & 0x7f800000) - 0x38000000) >> 13) & 0x7c00) | ((f >> 13) & 0x03ff)
    return h


def _half_to_float_UNUSED(half):
    # half is 16-bit int
    exp = (half >> 10) & 0x1f
    mant = half & 0x3ff
    if exp == 0:
        val = math.ldexp(mant, -24)
    elif exp != 31:
        val = math.ldexp(mant + 1024, exp - 25)
    elif mant == 0:
        val = float('inf')
    else:
        val = float('nan')
    if half & 0x8000:
        val = -val
    return val


def _half_to_float(half):
    # half is 16-bit int
    half = 0 + half
    single = (half & 0x7fff) << 13 | (half & 0x8000) << 16
    if (half & 0x7c00) != 0x7c00:
        return math.ldexp(struct.unpack(">f", struct.pack(">I", single))[0], 112)
    single |= 0x7f800000
    return struct.unpack(">f", struct.pack(">I", single))[0]


def _encode_float(data):
    encoded = b''

    if data == 0.0:
        if math.copysign(1.0, data) < 0: # -0.0
            encoded += bytes([0xf9, 0x80, 0x00])
        else: # 0.0
            encoded += bytes([0xf9, 0x00, 0x00])
    elif math.isinf(data):
        if math.copysign(1.0, data) < 0:
            encoded += bytes([0xf9, 0xfc, 0x00])
        else:
            encoded += bytes([0xf9, 0x7c, 0x00])
    elif math.isnan(data):
        encoded += bytes([0xf9, 0x7e, 0x00])
    else:
        single_array = array.array('f', [data])
        if single_array[0] == data:
            half = _single_to_half(single_array[0])
            if _half_to_float(half) == single_array[0]:
                encoded += bytes([(7 << 5) + 25])
                encoded += struct.pack('>H', half)
            else:
                encoded += bytes([(7 << 5) + 26])
                encoded += struct.pack('>f', single_array[0])
        else:
            encoded += bytes([(7 << 5) + 27])
            encoded += struct.pack('>d', data)

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
        encoded += _encode_float(data)
        return encoded


def _decode_int(value, data):
    if 0 <= value <= 23:
        return (1, value)
    elif value == 24:
        return (2, struct.unpack('>B', data[:1])[0])
    elif value == 25:
        return (3, struct.unpack('>H', data[:2])[0])
    elif value == 26:
        return (4, struct.unpack('>I', data[:4])[0])
    elif value == 27:
        return (5, struct.unpack('>Q', data[:8])[0])


def _decode_value(offset, data):
    major_type = data[offset] >> 5
    extra = data[offset] & ~(major_type << 5)
    value = None

    if major_type == 0:
        offset_inc, value = _decode_int(extra, data[1 + offset:])
        offset += offset_inc

    if major_type == 1:
        offset_inc, value = _decode_int(extra, data[1 + offset:])
        offset += offset_inc
        value = -1 - value

    if major_type == 2:
        offset_inc, value_len = _decode_int(extra, data[1 + offset:])
        offset += 1
        value = data[offset:offset + value_len]
        offset += offset_inc + value_len - 1

    if major_type == 3:
        offset_inc, value_len = _decode_int(extra, data[1 + offset:])
        offset += 1
        value = data[offset:offset + value_len].decode('utf8')
        offset += offset_inc + value_len - 1

    if major_type == 4:
        value = []
        if extra == 31:
            offset += 1
            while data[offset] != 0xFF:
                offset, item = _decode_value(offset, data)
                value.append(item)
        else:
            offset_inc, value_len = _decode_int(extra, data[1 + offset:])
            offset += offset_inc
            for i in range(0, value_len):
                offset, item = _decode_value(offset, data)
                value.append(item)

    if major_type == 5:
        value = {}
        if extra == 31:
            offset += 1
            while data[offset] != 0xFF:
                offset, key = _decode_value(offset, data)
                offset, item = _decode_value(offset, data)
                value[key] = item
        else:
            offset_inc, value_len = _decode_int(extra, data[1 + offset:])
            offset += offset_inc
            for i in range(0, value_len):
                offset, key = _decode_value(offset, data)
                offset, item = _decode_value(offset, data)
                value[key] = item

    simple = {
        20: False,
        21: True,
        22: None,
        23: None, # decode 'undefined' (23) as 'null' (22)
    }

    if major_type == 7:
        offset += 1
        if extra == 25: # half-precision
            half = struct.unpack('>H', data[offset:offset + 2])[0]
            value = _half_to_float(half)
            offset += 2
        elif extra == 26: # single-precision
            value = struct.unpack('>f', data[offset:offset + 4])[0]
            offset += 4
        elif extra == 27:
            value = struct.unpack('>d', data[offset:offset + 8])[0]
            offset += 8
        elif extra in simple:
            value = simple[extra]
        elif extra == 24:
            value = int(data[offset])
            offset += 1

    return (offset, value)


def decode(data):
    return _decode_value(0, data)[1]
