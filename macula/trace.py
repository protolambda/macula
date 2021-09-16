from typing import Callable, Protocol
from .step import Step, Address, Bytes32


# raw node access, can be tracked as global dictionary without pruning.
# Any node that is not found locally could be fetched lazily from an external trie.
class MPT(Protocol):
    def get_node(self, key: Bytes32) -> bytes: ...
    # note: key is computed as hash of the raw value (an RLP encoded MPT node)
    def put_node(self, raw: bytes) -> None: ...


class StepsTrace(Protocol):
    # returns the block header (RLP encoded), i.e. preimage of the block hash
    def block_header(self, block_hash: Bytes32) -> bytes: ...
    def world_accounts(self) -> MPT: ...
    def account_storage(self, address: Address) -> MPT: ...
    # code_hash is the sha3(code), not the account.
    # Necessary to get code that corresponds to the code-hash embedded in the account value.
    def code_lookup(self, code_hash: Bytes32) -> bytes: ...
    # persists code in an account, to retrieve by code_hash later
    def code_store(self, code: bytes) -> None: ...

    def last(self) -> Step: ...


Processor = Callable[[StepsTrace], Step]

