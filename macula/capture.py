from typing import Dict, Callable, List, Set
from remerkleable.tree import Gindex
from .step import Step, Bytes32, Address
from .trace import StepsTrace
from . import keccak_256
from .node_shim import ShimNode
from .mpt_work import MPT
from .external import ExternalSource


class CaptureMPT(MPT):
    node_getter: Callable[[bytes], bytes]

    # node hash -> node contents
    local_db: Dict[bytes, bytes]

    # track accessed nodes
    on_access: Callable[[Bytes32], None]

    def __init__(self, node_getter: Callable[[Bytes32], bytes], on_access: Callable[[Bytes32], None]):
        self.node_getter = node_getter
        self.on_access = on_access
        self.local_db = dict()

    def get_node(self, key: Bytes32) -> bytes:
        self.on_access(key)
        if key not in self.local_db:
            out = self.node_getter(key)
            self.local_db[key] = out
            return out
        else:
            return self.local_db[key]

    # note: key is computed as hash of the raw value (an RLP encoded MPT node)
    def put_node(self, raw: bytes) -> None:
        key = keccak_256(raw)  # key of the MPT node, not a path
        self.local_db[key] = raw


class StepAccessedKeys(object):
    # all the locations of binary tree nodes that were accessed
    step_gindices: Set[Gindex]
    # TODO: share these between world-nodes and account storage nodes?
    accessed_world_mpt_nodes: Set[Bytes32]
    accessed_acc_storage_mpt_nodes: Dict[Address, Set[Bytes32]]
    # Code-hashes that were accessed
    accessed_codes: Set[Bytes32]

    def __init__(self):
        self.step_gindices = set()
        self.accessed_world_mpt_nodes = set()
        self.accessed_acc_storage_mpt_nodes = dict()
        self.accessed_codes = set()


class CaptureTrace(StepsTrace):
    world_mpt: CaptureMPT
    acc_mpt_dict: Dict[Address, CaptureMPT]  # only contracts have an entry here
    codes: Dict[Bytes32, bytes]

    # per step, track which contents were accessed (may recurse into embedded step)
    access_trace: List[StepAccessedKeys]
    step_trace: List[Step]

    src: ExternalSource

    def __init__(self, src: ExternalSource):
        self.world_mpt = CaptureMPT(src.get_world_node, self.on_world_access)
        self.acc_mpt_dict = dict()
        self.codes = dict()
        self.step_trace = []
        self.access_trace = []
        self.src = src

    def on_world_access(self, key: Bytes32) -> None:
        self.access_trace[len(self.access_trace)-1].accessed_world_mpt_nodes.add(key)

    def world_accounts(self) -> MPT:
        return self.world_mpt

    def account_storage(self, address: Address) -> MPT:
        acc_track = self.access_trace[len(self.access_trace)-1].accessed_acc_storage_mpt_nodes
        if address not in acc_track:
            acc_track[address] = set()

        if address not in self.acc_mpt_dict:
            mpt = CaptureMPT(lambda key: self.src.get_acc_node(address, key), lambda key: acc_track[address].add(key))
            self.acc_mpt_dict[address] = mpt
            return mpt
        return self.acc_mpt_dict[address]

    def code_lookup(self, code_hash: Bytes32) -> bytes:
        self.access_trace[len(self.access_trace)-1].accessed_codes.add(code_hash)
        if code_hash not in self.codes:
            code = self.src.get_code(code_hash)
            self.codes[code_hash] = code
            return code
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
        # when producing the next step, we track what we access of this step.
        self.access_trace.append(StepAccessedKeys())

    def reset_shims(self):
        for step in self.steps:
            backing: ShimNode = step.get_backing()
            backing.reset_shim()

    def capture_access(self):
        last = self.last()
        shim: ShimNode = last.get_backing()
        access_list = list(shim.get_touched_gindices(g=1))
        last_access = self.access_trace[len(self.access_trace)-1]
        last_access.step_gindices.update(access_list)

