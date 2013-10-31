import collections
import json
import os


def get_diagnostics():
    tests = []
    example_path = os.path.join(os.path.dirname(__file__), 'diagnostics.txt')
    lines = open(example_path).readlines()[3:-1]

    decoder = json.JSONDecoder(object_pairs_hook=collections.OrderedDict)

    n = 0
    while n < len(lines):
        diagnostic = encoded = ''
        while n < len(lines) and lines[n].strip(' |\n') != '':
            _, d, e, _ = (x.strip() for x in lines[n].split('|'))
            diagnostic += d.strip()
            encoded += e.strip()
            n += 1
        n += 1

        # TODO Generate skipped tests for tests which are skipped

        # Skip tests with hex, strings, undefined lengths, tags, or undefined
        if diagnostic.startswith('h') or diagnostic.startswith('"\\u') \
                or '_' in diagnostic or '(' in diagnostic \
                or diagnostic == 'undefined':
            continue
        else:
            try:
                diagnostic = decoder.decode(diagnostic)
            except ValueError as e:
                # Skip tests which can't be decoded as JSON
                continue

        # Skip tests with floats or out of range ints
        if isinstance(diagnostic, float) or (isinstance(diagnostic, int) \
                and abs(diagnostic) >= (2 << 63) - 1):
            continue

        # Get the expected bytestring
        encoded = encoded[2:]
        encoded = bytes((int(encoded[i] + encoded[i+1], 16) \
                for i in range(0, len(encoded), 2)))

        tests.append((diagnostic, encoded))

    return tests


def pytest_generate_tests(metafunc):
    if all(x in metafunc.funcargnames for x in ('diagnostic', 'encoded')):
        for diagnostic, encoded in get_diagnostics():
            metafunc.addcall(funcargs={
                'diagnostic': diagnostic,
                'encoded': encoded
            })
