# pycbor

[![Build Status](https://travis-ci.org/michaelmior/pycbor.png)](https://www.travis-ci.org/michaelmior/pycbor)

pycbor supports all major types of RFC 7049 with the exception of semantic tagging.
There are probably some ways in which pycbor isn't strictly compliant, but it mostly works

## Usage

    >>> pycbor.encode([1, 2, 3])
    b'\x83\x01\x02\x03'

    >>> pycbor.decode(b'\x83\x01\x02\x03')
    [1, 2, 3]
