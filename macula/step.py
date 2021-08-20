from remerkleable.complex import Container, Vector, List
from remerkleable.byte_arrays import Bytes32, ByteVector
from remerkleable.basic import uint8, uint64, uint256, boolean
from .opcodes import OpCode

class Address(ByteVector[20]):
    def to_b32(self) -> Bytes32:
        return Bytes32(bytes(self).rjust(32))


class BlockHistory(Vector[Bytes32, 256]):
    pass


# TODO: 64 MiB memory maximum enough or too much? Every 2x makes the tree a layer deeper,
# but otherwise not much cost for unused space
class Memory(List[uint8, 64 << 20]):

    def append_zero_32_bytes(self) -> None:
        # TODO: if the length aligns to 32, this can be optimized
        for i in range(32):
            self.append(0)


def endian_swap_b32(v: Bytes32) -> Bytes32:
    return Bytes32(v[::-1])


# EVM stack is max 1024 words
class Stack(List[Bytes32, 1024]):

    def push_b32(self, b: Bytes32) -> None:
        self.append(b)

    def push_u256(self, b: uint256) -> None:  # TODO: hacky, SSZ uses little-endian, EVM uses big-endian
        self.append(endian_swap_b32(b.encode_bytes()))

    def pop_b32(self) -> Bytes32:
        v = self[len(self)-1]
        self.pop()
        return v

    def pop_u256(self) -> uint256:
        v = uint256.decode_bytes(endian_swap_b32(self[len(self)-1]))
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
        return uint256.decode_bytes(endian_swap_b32(self[len(self)-1]))

    # like peek, but write instead of read, to avoid pop/push overhead
    def tweak_b32(self, v: Bytes32):
        self[len(self)-1] = v

    def tweak_u256(self, v: uint256):
        self[len(self)-1] = endian_swap_b32(v.encode_bytes())

    def back_b32(self, n: int) -> Bytes32:
        length = len(self)
        if n+1 > length:
            raise Exception("bad stack access, interpreter bug")
        return self[length - n - 1]

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


class Step(Container):
    # Unused in the step itself, but important as output, to claim a state-root,
    # which can then be trusted by the next step.
    # Steps that access memory need to supply a separate (outside of the step sub-tree)
    # MPT-proof of the account and/or storage to access the data.
    state_root: Bytes32
    # Main mode of operation, to find the right kind of step execution at any given point
    exec_mode: uint8
    # History scope
    # ------------------
    # Most recent 256 blocks (excluding the block itself)
    block_hashes: BlockHistory
    # Block scope
    # ------------------
    # TODO: origin balance check for fee payment and value transfer
    coinbase: Address
    gas_limit: uint64
    block_number: uint64
    time: uint64
    difficulty: uint256
    base_fee: uint256
    # Tx scope
    # ------------------
    origin: Address
    tx_index: uint64
    gas_price: uint64

    # Contract scope
    # ------------------
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
    # Execution scope
    # ------------------
    # We generalize the opcode read from the code at PC,
    # and cache it here to not re-read the code every step of the opcode.
    # Ignored for starting-state (zeroed).
    op: uint8
    # The program-counter, index pointing to current executed opcode in the code
    pc: uint64
    # when splitting up operations further
    sub_index: uint64
    # true when the sub-operation is ongoing and must be completed still.
    sub_remaining: boolean
    # sub-computations need a place to track their inner state
    sub_data: SubData
    # When doing a return, continue with the operations after this step.
    return_to_step: uint64
    # Depending on the unwind mode: continue/return/out-of-gas/etc.
    unwind: uint64

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
