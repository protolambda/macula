try:
    from Crypto.Hash import keccak

    def keccak_256(x): return keccak.new(digest_bits=256, data=x).digest()
except ImportError:
    import sha3 as _sha3

    def keccak_256(x): return _sha3.keccak_256(x).digest()

import rlp


def rlp_decode_list(data: bytes) -> list:
    return rlp.decode(data, sedes=rlp.sedes.CountableList(rlp.sedes.Binary(allow_empty=True)))


def rlp_encode_list(items: list) -> bytes:
    return rlp.encode(items)
