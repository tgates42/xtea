#!/usr/bin/env python3

"""
Testvectors for XTEA found at:
 - http://www.tayloredge.com/reference/Mathematics/XTEA.pdf
 
"""


import xtea
from binascii import hexlify
from binascii import unhexlify

def _unwrap(s):
    return unhexlify(s.replace(' ',''))


if not __debug__:
    raise Exception("This script uses assert for tests. "
                    "Do use not -O or -OO to run it.")


TEST_VECTORS = [
    {
        'k': '27f917b1 c1da8993 60e2acaa a6eb923d',
        'p': 'af20a390 547571aa',
        'c': 'd26428af 0a202283'
    },

    {
        'k': '31415926 53589793 23846264 33832795',
        'p': '02884197 16939937',  # 48 digits of PI
        'c': '46e2007d 58bbc2ea',
    },
    {
        'k': '1234abc1 234abc12 34abc123 4abc1234',
        'p': 'abc1234a bc1234ab',
        'c': '5c0754c1 f6f0bd9b',
    },
    {
        'k': 'abc1234a bc1234ab c1234abc 1234abc1',
        'p': '234abc12 34abc123',
        'c': 'cdfcc72c 24bc116b',
    },
    {
        'k': 'deadbeef deadbeef deadbeef deadbeef',
        'p': 'deadbeef deadbeef',
        'c': 'faf28cb5 0940c0e0',
    },
    {
        'k': 'deadbeef deadbeef deadbeef deadbeef',
        'p': '9647a918 9ec565d5',
        'c': 'deadbeef deadbeef',
    },
]


def test_encryption():
    for i in range(len(TEST_VECTORS)):
        vector = TEST_VECTORS[i]
        e = _unwrap(vector['p'])
        c = _unwrap(vector['c'])
        k = _unwrap(vector['k'])

        x = xtea.new(key=k, mode=xtea.MODE_ECB)
        try:
            r = x.encrypt(e)
            assert r == c
        except AssertionError:
            print("Error on test %s:" % i)
            print("Expected %s, got %s!" % (hexlify(c).decode(),
                                            hexlify(r).decode()))
            raise
            

def test_decryption():
    for i in range(len(TEST_VECTORS)):
        vector = TEST_VECTORS[i]
        e = _unwrap(vector['p'])
        c = _unwrap(vector['c'])
        k = _unwrap(vector['k'])

        x = xtea.new(key=k, mode=xtea.MODE_ECB)
        try:
            r = x.decrypt(c)
            assert r == e
        except AssertionError:
            print("Error on test %s:" % i)
            print("Expected %s, got %s!" % (hexlify(e).decode(),
                                            hexlify(r).decode()))
            raise


if __name__ == "__main__":
    test_encryption()
    test_decryption()