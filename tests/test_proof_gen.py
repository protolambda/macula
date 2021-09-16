from typing import Dict, List, Optional, Set
from macula.opcodes import OpCode
from macula.trace import StepsTrace, MPT
from macula.step import Address, Bytes32, Step
from macula import keccak_256
from macula.exec_mode import ExecMode
from macula.interpreter import next_step
from macula.node_shim import ShimNode
from remerkleable.tree import Root, Gindex
from ethereum.trie import Trie
from ethereum.db import EphemDB
import rlp


def compile_test_ops(ops: list) -> bytes:
    return bytes(map(lambda x: int(x.value) if isinstance(x, OpCode) else int(x), ops))


class TestMPT(MPT):
    trie: Trie

    def __init__(self):
        self.trie = Trie(EphemDB())

    def get_node(self, key: Bytes32) -> bytes:
        db: EphemDB = self.trie.db
        return db.get(key)

    # note: key is computed as hash of the raw value (an RLP encoded MPT node)
    def put_node(self, raw: bytes) -> None:
        key = keccak_256(raw)  # key of the MPT node, not a path
        db: EphemDB = self.trie.db
        return db.put(key, raw)

    def mpt_root(self) -> Bytes32:
        return self.trie.root_hash

    # creates new nodes from root to value at key
    def insert(self, key: Bytes32, value: bytes):
        self.trie.update(key, value)


class TestTrace(StepsTrace):
    world_mpt: TestMPT
    acc_mpt_dict: Dict[Address, TestMPT]  # only contracts have an entry here
    codes: Dict[Bytes32, bytes]
    headers: Dict[Bytes32, bytes]

    steps: List[Step]

    # per step, track which contents were accessed (may recurse into embedded step)
    witness_tracker: List[Set[Gindex]]

    def __init__(self):
        self.world_mpt = TestMPT()
        self.acc_mpt_dict = dict()
        self.codes = dict()
        self.headers = dict()
        self.steps = []
        self.witness_tracker = []

    def block_header(self, block_hash: Bytes32) -> bytes:
        if block_hash not in self.headers:
            raise KeyError(f"could not find header {block_hash.hex()} in headers dict")
        return self.headers[block_hash]

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
        key = keccak_256(code)
        self.codes[key] = code

    def last(self) -> Step:
        if len(self.steps) == 0:
            raise Exception("step trace is empty, first step needs to be initialized still!")
        return self.steps[len(self.steps)-1]

    def add_step(self, step: Step) -> None:
        # wraps the internal tree backing, to track which nodes have been touched.
        step.set_backing(ShimNode.shim(step.get_backing()))

        self.steps.append(step)
        self.witness_tracker.append(set())

    def reset_shims(self):
        for step in self.steps:
            backing: ShimNode = step.get_backing()
            backing.reset_shim()

    def capture_access(self):
        last = self.last()
        shim: ShimNode = last.get_backing()
        access_list = list(shim.get_touched_gindices(g=1))
        self.witness_tracker[len(self.witness_tracker)-1].update(access_list)

        # reset shims, next capture will cleanly represent just what was accessed by the last step
        self.reset_shims()

    def inject_acct(self, address: Address, nonce: int = 0, balance: int = 0,
                    code: bytes = b"", storage: Optional[TestMPT] = None):
        mpt_key = keccak_256(address)
        storage_root = b""
        if storage is not None:
            storage_root = storage.mpt_root()
        code_hash = keccak_256(code)
        acc_rlp_li = [nonce, balance, storage_root, code_hash]
        acc_rlp = rlp.encode(acc_rlp_li)
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
    trac = TestTrace()
    step = Step()
    step.contract.code = code
    step.contract.gas = 1000
    step.exec_mode = ExecMode.CallPre.value
    trac.add_step(step)

    SAFETY_LIMIT = 1000
    i = 0
    while i < SAFETY_LIMIT:
        next = next_step(trac)
        trac.capture_access()
        trac.add_step(next)

        mode = trac.last().exec_mode
        if mode == ExecMode.DONE.value:
            break

    if i >= SAFETY_LIMIT:
        raise Exception("stopped interpreter, too many steps, infinite loop?", step)

    for i, step, access in zip(range(len(trac.steps)), trac.steps, trac.witness_tracker):
        print(f"step {i}: {step.hash_tree_root().hex()} -- {ExecMode(step.exec_mode)}, {OpCode(step.contract.op)}")
        for gindex in access:
            print(f"    {bin(gindex)[2:].ljust(20, ' ')}: ", step.get_backing().getter(gindex).merkle_root().hex())
    print("return data:", bytes(trac.last().contract.ret_data).hex())


ONE_ETHER = 1_000_000_000_000_000_000

def test_execute_contract():
    foobar_storage = TestMPT()
    foobar_storage.insert(b"\x00" * 31 + b"\x00", b"\xcd" * 32)
    foobar_storage.insert(b"\x00" * 31 + b"\x01", b"\xef" * 32)
    # TODO: contract code
    foobar_code = compile_test_ops([OpCode.PUSH1, 1])
    foobar_addr = Address(b"\xab"*20)

    trac = TestTrace()
    trac.inject_acct(address=foobar_addr, nonce=0, balance=42*ONE_ETHER, code=foobar_code, storage=foobar_storage)

    # TODO: create transaction that calls foobar contract
    # TODO: load transaction into first step
    # TODO: run interpreter

