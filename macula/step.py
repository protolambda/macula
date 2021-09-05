from typing import Optional, BinaryIO, Union as PyUnion, Any
from remerkleable.complex import Container, Vector, List, Type, TypeVar
from remerkleable.union import Union
from remerkleable.byte_arrays import Bytes32, ByteVector, ByteList
from remerkleable.basic import uint8, uint64, uint256, boolean
from remerkleable.core import BackedView, View, Node, ViewHook, ObjType
from .opcodes import OpCode

class Address(ByteVector[20]):
    def to_b32(self) -> Bytes32:
        return Bytes32(bytes(self).rjust(32))

    @staticmethod
    def from_b32(v: Bytes32) -> "Address":
        return Address(v[:20])


class BlockHistory(Vector[Bytes32, 256]):
    pass


# TODO: 64 MiB memory maximum enough or too much? Every 2x makes the tree a layer deeper,
# but otherwise not much cost for unused space
class Memory(List[uint8, 64 << 20]):

    def append_zero_32_bytes(self) -> None:
        # TODO: if the length aligns to 32, this can be optimized
        for i in range(32):
            self.append(0)

    def get_ptr_32_bytes(self, offset: uint64) -> Bytes32:
        # note: gas and memory size checks ensure the below is safe from
        # over/under-flows and out-of-bound reads.
        if len(self) > offset:
            # note: may not align with 32-byte tree leaf values
            # (bytes are packed together in the binary tree that backs the memory),
            # but can be read in max 2 adjacent leaf nodes.
            return Bytes32(self[offset:offset+32])
        return Bytes32()

    def set_32_bytes(self, offset: uint64, val: Bytes32):
        if offset + 32 > len(self):
            raise Exception("invalid memory access, must be a bug")
        # note: alignment, either touches one or two tree leaf nodes.
        self[offset:offset+32] = val


def uint256_to_b32(v: uint256) -> Bytes32:
    return v.encode_bytes()  # uint256 is configured to be big-endian in the remerkleable settings


def b32_to_uint256(v: Bytes32) -> uint256:
    return uint256.decode_bytes(v)  # uint256 is configured to be big-endian in the remerkleable settings


# EVM stack is max 1024 words
class Stack(List[Bytes32, 1024]):

    def push_b32(self, b: Bytes32) -> None:
        self.append(b)

    def push_u256(self, b: uint256) -> None:
        self.append(uint256_to_b32(b))

    def pop_b32(self) -> Bytes32:
        v = self[len(self)-1]
        self.pop()
        return v

    def pop_u256(self) -> uint256:
        v = b32_to_uint256(self[len(self)-1])
        self.pop()
        return v

    def dup(self, n: int) -> None:
        self.append(self[len(self)-n])

    def swap(self, n: int) -> None:
        l = len(self)
        a = self[l-1]
        b = self[l-n]
        self[l-n] = a
        self[l-1] = b

    def peek_b32(self) -> Bytes32:
        return self[len(self)-1]

    def peek_u256(self) -> uint256:
        return b32_to_uint256(self[len(self)-1])

    # like peek, but write instead of read, to avoid pop/push overhead
    def tweak_b32(self, v: Bytes32):
        self[len(self)-1] = v

    def tweak_u256(self, v: uint256):
        self[len(self)-1] = uint256_to_b32(v)

    def tweak_back_b32(self, v: Bytes32, n: int):
        length = len(self)
        if n+1 > length:
            raise Exception("bad stack access, interpreter bug")
        self[length-n-1] = v

    def tweak_back_u256(self, v: uint256, n: int):
        length = len(self)
        if n+1 > length:
            raise Exception("bad stack access, interpreter bug")
        self[length-n-1] = uint256_to_b32(v)

    def back_b32(self, n: int) -> Bytes32:
        length = len(self)
        if n+1 > length:
            raise Exception("bad stack access, interpreter bug")
        return self[length - n - 1]

    def back_u256(self, n: int) -> uint256:
        length = len(self)
        if n+1 > length:
            raise Exception("bad stack access, interpreter bug")
        return b32_to_uint256(self[length - n - 1])


# Needs to be as big as memory, all of it can be returned
class ReturnData(List[uint8, 64 << 20]):
    pass


# See https://github.com/ethereum/EIPs/blob/master/EIPS/eip-170.md
# ~24.5 KB
class Code(List[uint8, 0x6000]):

    def get_op(self, pc: uint64) -> OpCode:
        if pc >= self.length():
            return OpCode.STOP
        else:
            return OpCode(self[pc])

    def valid_jump_dest(self, dest: uint256) -> bool:
        # PC cannot go beyond len(code) and certainly can't be bigger than 63bits.
        # Don't bother checking for JUMPDEST in that case.
        if int(dest) >= len(self):
            return False
        # Only JUMPDESTs allowed for destinations
        if self[dest] != uint8(OpCode.CALL.value):
            return False
        # TODO: jump-dest analysis is missing! Cannot jump into data segment.
        # we likely want to cache jump-dest analysis in the step data to not repeat it for every step
        return True


# Assuming a tx input can be max 400M gas, and 4 gas is paid per zero byte, then put a 100M limit on input.
class Input(List[uint8, 100_000_000]):
    # returns a slice from the data based on the start and size and pads
    # up to size with zero's. This function is overflow safe.
    def get_data_b32(self, start: uint64) -> Bytes32:
        length = len(self)
        if start > length:
            return Bytes32()
        end = start + 32
        if end > length:
            return Bytes32(bytes(self[start:length]).ljust(32))
        else:
            return Bytes32(self[start:length])


# 1024 words to track sub-step progress. Not to be confused with the memory scratchpad slots.
# TODO: any operations that need more scratch space?
class SubData(Vector[Bytes32, 1024]):
    pass


V = TypeVar('V', bound="View")


# Util to make recursive Step data types work. Lazy-loads the step type info on usage.
class LazyStep(BackedView):

    @classmethod
    def coerce_view(cls: Type[V], v: Any) -> V:
        return Step.coerce_view(v)

    @classmethod
    def default_node(cls) -> Node:
        return Step.default_node()

    @classmethod
    def view_from_backing(cls: Type[V], node: Node, hook: Optional[ViewHook[V]] = None) -> V:
        return Step.view_from_backing(node, hook)

    @classmethod
    def is_fixed_byte_length(cls) -> bool:
        return False

    @classmethod
    def min_byte_length(cls) -> int:
        return 0

    @classmethod
    def max_byte_length(cls) -> int:
        raise Exception("unlimited")

    @classmethod
    def decode_bytes(cls: Type[V], bytez: bytes) -> V:
        return LazyStep(backing=Step.decode_bytes(bytez).get_backing())

    @classmethod
    def deserialize(cls: Type[V], stream: BinaryIO, scope: int) -> V:
        return LazyStep(backing=Step.deserialize(stream, scope).get_backing())

    @classmethod
    def from_obj(cls: Type[V], obj: ObjType) -> V:
        return LazyStep(backing=Step.from_obj(obj).get_backing())

    @classmethod
    def type_repr(cls) -> str:
        return "LazyStep"


# noinspection PyAbstractClass
class RecursiveStep(Union[None, LazyStep]):
    def value(self) -> PyUnion[None, View]:
        val: PyUnion[None, LazyStep] = super(RecursiveStep, self).value()
        if val is None:
            return None
        else:
            return Step(backing=val.get_backing(), hook=val._hook)


class HistoryScope(Container):
    # Most recent 256 blocks (excluding the block itself). Trick: ring-buffer, key = number % 256
    block_hashes: BlockHistory


class BlockScope(Container):
    # TODO: origin balance check for fee payment and value transfer
    coinbase: Address
    gas_limit: uint64
    block_number: uint64
    time: uint64
    difficulty: uint256
    base_fee: uint256


class TxScope(Container):
    origin: Address
    tx_index: uint64
    gas_price: uint64


class ContractScope(Container):
    to: Address
    create: boolean
    call_depth: uint64
    caller: Address
    memory: Memory
    # expanding memory costs exponentially more gas, for the difference in length
    memory_last_gas: uint64
    # We compute the memory size, charge for it first, and only then allocate it.
    memory_desired: uint64
    stack: Stack
    ret_data: ReturnData
    code: Code
    code_hash: Bytes32
    code_addr: Address
    input: Input
    gas: uint64
    value: uint256
    # Make storage read-only, to support STATIC-CALL
    read_only: boolean

    # return false if out of gas
    def use_gas(self, delta: uint64) -> bool:
        pre_gas = self.gas
        if delta > pre_gas:
            return False
        self.gas = pre_gas - delta
        return True

    def return_gas(self, delta: uint64) -> None:
        # no overflow, assuming gas total is capped within uint64
        self.gas += delta


class ExecutionScope(Container):
    # We generalize the opcode read from the code at PC,
    # and cache it here to not re-read the code every step of the opcode.
    # Ignored for starting-state (zeroed).
    op: uint8
    # The program-counter, index pointing to current executed opcode in the code
    pc: uint64
    # when splitting up operations further
    sub_index: uint64
    # sub-computations need a place to track their inner state
    sub_data: SubData
    # When doing a return, continue with the operations after this step.
    return_to_step: RecursiveStep


class StateWorkMode(Enum):
    NO_ACTION = 0

    HAS_ACCOUNT = 1
    CREATE_ACCOUNT = 2

    SUB_BALANCE = 3
    ADD_BALANCE = 4

    READ_CONTRACT_CODE_HASH = 5
    READ_CONTRACT_CODE = 6
    REMOVE_CONTRACT_CODE = 7

    READ_NONCE = 8
    SET_NONCE = 9

    STORAGE_READ = 10
    STORAGE_WRITE = 11

    # TODO: more state ops


class StateWork_HasAccount(Container):
    address: Address
    result: boolean

class StateWork_CreateAccount(Container):
    address: Address
    balance: uint256
    nonce: uint256
    code_hash: Bytes32

class StateWork_SubBalance(Container):
    address: Address
    sub_value: uint256

class StateWork_AddBalance(Container):
    address: Address
    add_value: uint256

class StateWork_ReadContractCodeHash(Container):
    address: Address
    code_hash_result: Bytes32

class StateWork_ReadContractCode(Container):
    address: Address
    code: Code

class StateWork_RemoveContractCode(Container):
    address: Address

class StateWork_ReadNonce(Container):
    address: Address
    nonce_result: uint256

class StateWork_SetNonce(Container):
    address: Address
    nonce: uint256

class StateWork_StorageRead(Container):
    address: Address
    key: Bytes32
    value_result: Bytes32

class StateWork_StorageWrite(Container):
    address: Address
    key: Bytes32
    value: Bytes32


StateWork = Union[  # All these must match the enum StateWorkMode
    None,                            # NO_ACTION
    StateWork_HasAccount,            # HAS_ACCOUNT
    StateWork_CreateAccount,         # CREATE_ACCOUNT
    StateWork_SubBalance,            # SUB_BALANCE
    StateWork_AddBalance,            # ADD_BALANCE
    StateWork_ReadContractCodeHash,  # READ_CONTRACT_CODE_HASH
    StateWork_ReadContractCode,      # READ_CONTRACT_CODE
    StateWork_RemoveContractCode,    # REMOVE_CONTRACT_CODE
    StateWork_ReadNonce,             # READ_NONCE
    StateWork_SetNonce,              # SET_NONCE
    StateWork_StorageRead,           # STORAGE_READ
    StateWork_StorageWrite,          # STORAGE_WRITE
]

class StateWorkScope(Container):
    # Manages state machine during the StateWork execution mode
    state_work: StateWork
    # Once the work is done, this is set to True,
    # to carry over the work in the parent step without falling back in the same state work routine.
    done: boolean


class MPTWorkScope(Container):
    # On a read: recurse from top to bottom, then store bottom node
    # On a write: recurse from top to bottom, modify to write, then unwind back
    # On a delete: recurse from top to bottom, delete, propagate deletion, unwind back,
    #  and collapse branch nodes where necessary by grafting the remaining branch child and parent.

    # Instructs which trie to operate on
    # (for the DB it really doesn't matter, as we access all nodes by the hash of the node contents,
    #  but to map it to the right API calls on retrieval it's still useful)
    mpt_tree_source: uint8  # see MPTTreeSource enum
    mpt_start_reference: Bytes32  # the starting point, to identify e.g. an account

    # Manages state machine during the MPTWork execution mode
    mpt_mode: uint8  # see MPTAccessMode enum
    # what to write at the mpt_lookup_key, if in writing mode,
    # only used to start writing once done with the reading part.
    mpt_write_root: ByteList[32]
    # after finishing the mode, continue with this next mode.
    mpt_mode_on_finish: uint8

    # the step that has step.mpt_value that represents the parent of the current node
    mpt_parent_node_step: RecursiveStep

    # The current node (to expand or to bubble up)
    # If the RLP-encoded node fits in less than 32 bytes, it's embedded instead of stored in the DB.
    # If does not fit, then we store the hash (*NOT* RLP encoded), which is 32 bytes.
    mpt_current_root: ByteList[32]  # max 32 bytes. Smaller values than 32 are not hashed.
    # if the node corresponding to the key cannot be found
    # traversal stops with this failure marker. Non-zero if failure.
    mpt_fail_lookup: uint8

    # Note: First nibble of key = most significant nibble of uint256
    # I.e., to read the next nibble, shift left by 4 bits
    mpt_lookup_key: uint256
    # how many nibbles of the key we need to read
    mpt_lookup_key_nibbles: uint64
    # how much of the key has been read
    mpt_lookup_nibble_depth: uint64

    # When removing branch nodes, and grafting remaining child with parent,
    # track the part of the key to insert between the two. Can be empty.
    # First nibble is the most significant, like mpt_lookup_key
    mpt_graft_key_segment: uint256
    # Length in nibbles of the segment
    mpt_graft_key_nibbles: uint64

    # Result of reading. Assumed to fit in 2048 bytes. (contract code is only referenced by hash)
    # E.g. RLP-encoded account
    mpt_value: ByteList[2048]


class Step(Container):
    state_root: Bytes32

    # Main mode of operation, to find the right kind of step execution at any given point
    exec_mode: uint8

    history_scope: HistoryScope
    block_scope: BlockScope
    tx_scope: TxScope
    contract_scope: ContractScope
    state_work_scope: StateWorkScope
    mpt_work_scope: MPTWorkScope
