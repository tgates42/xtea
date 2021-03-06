"""
XTEA-Cipher in Python (eXtended Tiny Encryption Algorithm)

XTEA is a blockcipher with 8 bytes blocksize and 16 bytes Keysize (128-Bit).
The algorithm is secure at 2014 with the recommend 64 rounds (32 cycles). This
implementation supports following modes of operation:
ECB, CBC, CFB, OFB, CTR

Example:

>>> from xtea4 import *
>>> key = " "*16  # Never use this
>>> text = "This is a text. "*8
>>> x = new(key, mode=MODE_OFB, IV="12345678")
>>> c = x.encrypt(text)
>>> c.encode("hex")
'fa66ec11b82e38bc77c14be093bb8aa0d7fe0fb9e6ec015
7a22d254fee43aea9a64c8dbb2c2b899f66800f264419c8e
8796ad8f94c7758b916428019d10573943324a9dcf60f883
1f0f925cd7215e5dd4f1334d9ee242d41ac02d0a64c49663
e5897bfd2450982379267e6cd7405b477ccc19d6c0d32e2f
887b76fe01d621a8d'
>>> text == x.decrypt(c)
True
"""

from __future__ import print_function

import struct
import binascii
import sys
import warnings

from .counter import Counter

MODE_ECB = 1
MODE_CBC = 2
MODE_CFB = 3
MODE_PGP = 4
MODE_OFB = 5
MODE_CTR = 6

PY_3 = sys.version_info.major >= 3

if PY_3:

    def b_ord(n):
        return n

    def b_chr(n):
        return bytes([n])
else:

    def b_ord(n):
        return ord(n)

    def b_chr(n):
        return chr(n)


block_size = 64
key_size = 128


def new(key, **kwargs):
    """Create an "XTEACipher" object.
    It fully PEP-272 comliant, default mode is ECB.
    Args:
        key (bytes): The key for encrytion/decryption. Must be 16 in length

    Kwargs:

        mode (int): Mode of operation, must be one of this::
            1 = ECB
            2 = CBC
            3 = CFB
            5 = OFB
            6 = CTR
        
        IV (bytes): Initialisation vector (needed with CBC/CFB).
            Must be 8 in length.
        
        counter (callable object): a callable counter wich returns bytestrings

            .. versionchanged:: 0.5.0
               Only callable objects returning bytestrings can be used,
               previously integers instead of callables were allowed, too.
        
        endian (char / string):
            how data is beeing extracted (default "!" = big endian)
            ..seealso:: modules :py:mod:`struct`

        rounds (int / float): How many rounds are going to be used,
            one round are two cycles, there are no *half* cycles.
            The minimum secure rounds are 37 (default 64)

    Raises:
        ValueError if invalid/not all data is given.
        NotImplementedError on MODE_PGP

    Returns:
       XTEACipher object

    """
    return XTEACipher(key, **kwargs)


################ XTEACipher class


class XTEACipher(object):
    """The cipher class

    Functions:
    encrypt -- encrypt data
    decrypt -- decrypt data

    _block -- splits the data in blocks (you may need padding)

    Constants:
    block_size = 8

    Variables:
    IV -- the initialisation vector (default None or "\00"*8)
    counter -- counter for CTR (default None)
    
    """

    block_size = 8
    IV = None
    counter = None

    def __init__(self, key, **kwargs):
        """\
        Alternative constructor.
        Create an cipher object.

        Args:
            key (bytes): The key for encrytion/decryption. Must be 16 in length

        Kwargs:
            mode (int): Mode of operation, must be one of this::

                1 = ECB
                2 = CBC
                3 = CFB
                5 = OFB
                6 = CTR

            IV (bytes): Initialisation vector (needed with CBC/CFB).
                Must be 8 in length.

            counter (callable object): a callable counter wich returns bytes
                or int (needed with CTR)
      
            endian (char / string):
                how data is beeing extracted (default "!")
                ..seealso:: modules :py:mod:`struct`

        Raises:
            ValueError if invalid/not all required data is give.
            NotImplementedError on MODE_PGP.

        Creates:
            XTEACipher object

        """

        self.key = key
        if len(key) != key_size / 8:  # Check key len
            raise ValueError("Key must be 128 bit long")

        keys = kwargs.keys()  # arguments

        self.mode = kwargs.get("mode")

        if self.mode == None:
            self.mode = MODE_ECB  # if not given
            warnings.warn("Using implicit ECB!")

        if self.mode not in (
                MODE_ECB, MODE_CBC, MODE_CFB, MODE_OFB, MODE_CTR):
            raise NotImplementedError(
                "The selected mode of operation does not exist.")

        self.IV = kwargs.get("IV")

        # cbc, cfb and ofb need an iv
        if self.mode in (MODE_CBC, MODE_CFB, MODE_OFB) and (
                self.IV is None or len(self.IV) != self.block_size):
            raise ValueError(
                "CBC, CFB and OFB need an IV with a length of 8 bytes!")

        self.counter = kwargs.get("counter")

        if self.mode == MODE_CTR and not callable(self.counter): 
            raise ValueError("CTR mode needs a callable counter")

        self.rounds = int(kwargs.get("rounds", 64))
        self.endian = kwargs.get("endian", "!")

        if self.mode == MODE_OFB:

            def keygen():
                while True:
                    self.IV = _encrypt(self.key, self.IV, self.rounds // 2)
                    for k in self.IV:
                        yield b_ord(k)

            self._keygen = keygen()

        elif self.mode == MODE_CTR:

            def keygen():
                while True:
                    self.IV = _encrypt(self.key,
                                       self.counter(), self.rounds // 2)
                    for k in self.IV:
                        yield b_ord(k)

            self._keygen = keygen()

    def encrypt(self, data):
        """\
        Encrypt data, it must be a multiple of 8 in length except for
        CTR and OFB mode of operation. When using the OFB or CTR mode, the
        function for encryption and decryption is the same.

        Args:
            data (bytes): The data to encrypt.
        Returns:
            bytestrings
        Raises:
            ValueError
        """

        if self.mode in (MODE_OFB, MODE_CTR):
            return self._stream(data)

        args = (self.rounds // 2, self.endian)

        out = []
        blocks = self._block(data)

        for block in blocks:
            if self.mode == MODE_ECB:
                ecd = _encrypt(self.key, block, *args)
            elif self.mode == MODE_CBC:
                xored = xor_strings(self.IV, block)
                ecd = self.IV = _encrypt(self.key, xored, *args)
            elif self.mode == MODE_CFB:
                keystream = _encrypt(self.key, self.IV, *args)
                ecd = self.IV = xor_strings(keystream, block)
            else:
                raise ValueError("Unknown mode of operation!")

            out.append(ecd)

        return b"".join(out)


    def decrypt(self, data):
        """\
        Decrypt data, it must be a multiple of 8 in length except for
        CTR and OFB mode of operation. When using the OFB or CTR mode, the
        function for encryption and decryption is the same.

        Args:
            data (bytes): The data to decrypt.
        Returns:
            bytestrings
        Raises:
            ValueError
        """

        if self.mode in (MODE_OFB, MODE_CTR):
            return self._stream(data)

        args = (self.rounds // 2, self.endian)

        out = []
        blocks = self._block(data)

        for block in blocks:
            if self.mode == MODE_ECB:
                dec = _decrypt(self.key, block, *args)
            elif self.mode == MODE_CBC:
                decrypted_but_not_xored = _decrypt(self.key, block, *args)
                dec = xor_strings(self.IV, decrypted_but_not_xored)
                self.IV = block
            elif self.mode == MODE_CFB:
                keystream = _encrypt(self.key, self.IV, *args)
                dec = xor_strings(keystream, block)
                self.IV = block
            else:
                raise ValueError("Unknown mode of operation!")

            out.append(dec)

        return b"".join(out)


    def _stream(self, data):
        xor = [b_chr(x ^ y) for (x, y) in zip(map(b_ord, data), self._keygen)]
        return b"".join(xor)

    def _block(self, s):
        l = []
        rest_size = len(s) % self.block_size
        if rest_size:
            raise ValueError("Input string must be a multiple of blocksize "
                             "in length")
        for i in range(len(s) // self.block_size):
            l.append(s[i * self.block_size:((i + 1) * self.block_size)])
        return l


################ Util functions: basic encrypt/decrypt, OFB, xor, stringToLong
"""
This are utilities only, use them only if you know what you do.

Functions:
_encrypt -- Encrypt one single block of data.
_decrypt -- Decrypt one single block of data.
xor_strings -- xor to strings together.
"""


def _encrypt(key, block, n=32, endian="!"):
    """Encrypt one single block of data.

    Only use if you know what to do.

    Keyword arguments:
    key -- the key for encrypting (and decrypting)
    block  -- one block plaintext
    n -- cycles, one cycle is two rounds, more cycles
          -> more security and slowness (default 32)
    endian -- how struct will handle data (default "!" (big endian/network))
    """
    v0, v1 = struct.unpack(endian + "2L", block)
    k = struct.unpack(endian + "4L", key)
    sum, delta, mask = 0, 0x9e3779b9, 0xffffffff
    for round in range(n):
        v0 = (v0 + (((v1 << 4 ^ v1 >> 5) + v1) ^ (sum + k[sum & 3]))) & mask
        sum = (sum + delta) & mask
        v1 = (v1 +
              (((v0 << 4 ^ v0 >> 5) + v0) ^ (sum + k[sum >> 11 & 3]))) & mask
    return struct.pack(endian + "2L", v0, v1)


def _decrypt(key, block, n=32, endian="!"):
    """Decrypt one single block of data.

    Only use if you know what to do.

    Keyword arguments:
    key -- the key for encrypting (and decrypting)
    block  -- one block ciphertext
    n -- cycles, one cycle is two rounds, more cycles =
          -> more security and slowness (default 32)
    endian -- how struct will handle data (default "!" (big endian/network))
    """
    v0, v1 = struct.unpack(endian + "2L", block)
    k = struct.unpack(endian + "4L", key)
    delta, mask = 0x9e3779b9, 0xffffffff
    sum = (delta * n) & mask
    for round in range(n):
        v1 = (v1 -
              (((v0 << 4 ^ v0 >> 5) + v0) ^ (sum + k[sum >> 11 & 3]))) & mask
        sum = (sum - delta) & mask
        v0 = (v0 - (((v1 << 4 ^ v1 >> 5) + v1) ^ (sum + k[sum & 3]))) & mask
    return struct.pack(endian + "2L", v0, v1)


if PY_3:

    def xor_strings(s, t):
        """xor to strings together.

        Keyword arguments:
        s -- string one
        t -- string two
        """
        return bytes([(x ^ y) for x, y in zip(s, t)])
else:

    def xor_strings(s, t):
        """xor to strings together.

        Keyword arguments:
        s -- string one
        t -- string two
        """
        return "".join(chr(ord(x) ^ ord(y)) for x, y in zip(s, t))
