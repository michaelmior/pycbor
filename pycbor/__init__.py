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
    f = struct.unpack('>I', struct.pack('>f', single))[0]

    # http://stackoverflow.com/questions/6162651/
    # Check if float is subnormal
    if f < 0x38800000:
        # Too small for subnormal, must use +/- 0.0
        if f < 0x33000000:
            return math.copysign(single, 0.0)

        # Get sign bit and temporary exponent
        sign = (f >> 16) & 0x8000
        val = (f & 0x7fffffff ) >> 23

        # Add the subnormal bit, round, divde by 2^(1-(exp-127+15))
        # and >> 13 | exp=0
        return sign | ((f & 0x7fffff | 0x800000)
                        + (0x800000 >> val - 102)
                        >> 126 - val) # div by 2^(1-(exp-127+15)) and >> 13 | exp=0
    else:
        # ftp://ftp.fox-toolkit.org/pub/fasthalffloatconversion.pdf
        # 1) Sign bit is shifted and masked;
        # 2) Exponent (5 bits) is masked and bias-correction subtracted; result shifted and masked;
        # 3) Mantissa (10 bits) is shifted and masked;
        # Result is assembled by or-ing those 3.
        # This ignores rounding and doesn't handle zero, inf, nan or subnormals.
        return ((f >> 16) & 0x8000) | \
                ((((f & 0x7f800000) - 0x38000000) >> 13) & 0x7c00) | \
                ((f >> 13) & 0x03ff)


def _half_to_float(half):
    # Half is 16-bit int
    single = (half & 0x7fff) << 13 | (half & 0x8000) << 16
    if (half & 0x7c00) != 0x7c00:
        mant = half & 0x03ff
        exp = half & 0x7c00
        if mant and exp == 0:
            exp = 0x1c400

            while (mant & 0x400) == 0:
                mant <<= 1
                exp -= 0x400

            mant &= 0x3ff
            single = (half & 0x8000) << 16 | (exp | mant) << 13

            return struct.unpack('>f', struct.pack('>I', single))[0]

        return math.ldexp(struct.unpack('>f', struct.pack('>I', single))[0], 112)

    single |= 0x7f800000
    return struct.unpack('>f', struct.pack('>I', single))[0]


def _encode_float(data):
    encoded = b''

    if data == 0.0:
        if math.copysign(1.0, data) < 0:
            # -0.0
            encoded += b'\xf9\x80\x00'
        else:
            # 0.0
            encoded += b'\xf9\x00\x00'
    elif math.isinf(data):
        if math.copysign(1.0, data) < 0:
            encoded += b'\xf9\xfc\x00'
        else:
            encoded += b'\xf9\x7c\x00'
    elif math.isnan(data):
        encoded += b'\xf9\x7e\x00'
    else:
        single_array = array.array('f', [data])
        if single_array[0] == data:
            half = _single_to_half(single_array[0])

            if _half_to_float(half) == single_array[0]:
                # Half-precision
                encoded += bytes([(7 << 5) + 25])
                encoded += struct.pack('>H', half)
            else:
                # Single-precision
                encoded += bytes([(7 << 5) + 26])
                encoded += struct.pack('>f', single_array[0])
        else:
            # Double-precision
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
        if extra == 31:
            offset += 1
            value = b''
            while data[offset] != 0xFF:
                offset, item = _decode_value(offset, data)
                value += bytes(item)
            offset += 1
        else:
            offset_inc, value_len = _decode_int(extra, data[1 + offset:])
            offset += 1
            value = data[offset:offset + value_len]
            offset += offset_inc + value_len - 1

    if major_type == 3:
        if extra == 31:
            offset += 1
            value = ''
            while data[offset] != 0xFF:
                offset, item = _decode_value(offset, data)
                value += item
            offset += 1
        else:
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
            offset += 1
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
            offset += 1
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

        if extra == 25:
            # Half-precision
            half = struct.unpack('>H', data[offset:offset + 2])[0]
            value = _half_to_float(half)
            offset += 2
        elif extra == 26:
            # Single-precision
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
