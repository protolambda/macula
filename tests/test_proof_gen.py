from typing import Dict, List, Optional
from macula.opcodes import OpCode
from macula.trace import StepsTrace, MPT
from macula.step import Address, Bytes32, Step
from macula.mpt_proof_trace import rlp_encode_list

def eth_sha3() -> Bytes32:
    return Bytes32()  # TODO


def compile_test_ops(ops: list) -> bytes:
    return bytes(map(lambda x: int(x.value) if isinstance(x, OpCode) else int(x), ops))


class TestMPT(MPT):  # TODO, wrap a MPT python lib for testing
    def get_node(self, key: bytes) -> bytes: ...
    # note: key is computed as hash of the raw value (an RLP encoded MPT node)
    def put_node(self, raw: bytes) -> None: ...

    def mpt_root(self) -> Bytes32:
        return Bytes32()

    def insert(self, key: bytes, value: bytes): ...  # creates new nodes from root to value at key


class TestTrace(StepsTrace):
    world_mpt: TestMPT
    acc_mpt_dict: Dict[Address, TestMPT]  # only contracts have an entry here
    codes: Dict[Bytes32, bytes]
    steps: List[Step]
    steps_by_root: Dict[Bytes32, Step]

    def __init__(self):
        self.world_mpt = TestMPT()
        self.acc_mpt_dict = dict()
        self.codes = dict()
        self.steps = []
        self.steps_by_root = dict()

    def world_accounts(self) -> MPT:
        return self.world_mpt

    def account_storage(self, address: Address) -> MPT:
        if address not in self.acc_mpt_dict:
            raise KeyError(f"could not find address {address.hex()} in account storage")
        return self.acc_mpt_dict[address]

    def code_lookup(self, code_hash: Bytes32) -> bytes:
        if code_hash not in self.codes:
            raise KeyError(f"could not find code {code_hash.hex()} in codes dict")
        return self.codes[code_hash]

    def code_store(self, code: bytes) -> None:
        key = eth_sha3(code)
        self.codes[key] = code

    def last(self) -> Step:
        if len(self.steps) == 0:
            raise Exception("step trace is empty, first step needs to be initialized still!")
        return self.steps[len(self.steps)-1]

    def by_root(self, key: Bytes32) -> Step:
        return self.steps_by_root[key]

    def add_step(self, step: Step) -> None:
        self.steps.append(step)
        self.steps[step.hash_tree_root()] = step

    def inject_acct(self, address: Address, nonce: int = 0, balance: int = 0,
                    code: bytes = b"", storage: Optional[TestMPT] = None):
        mpt_key = eth_sha3(address)
        storage_root = b""
        if storage is not None:
            storage_root = storage.mpt_root()
        code_hash = eth_sha3(code)
        acc_rlp_li = [nonce, balance, storage_root, code_hash]
        acc_rlp = rlp_encode_list(acc_rlp_li)
        self.world_mpt.insert(mpt_key, acc_rlp)
        if storage is not None:
            self.acc_mpt_dict[address] = storage
        self.codes[code_hash] = code


def test_execute():
    ops = [
        OpCode.PUSH1, 10,
        OpCode.PUSH1, 0,
        OpCode.MSTORE,
        OpCode.PUSH1, 32,
        OpCode.PUSH1, 0,
        OpCode.RETURN
    ]
    code = compile_test_ops(ops)
    print("code", code.hex())

