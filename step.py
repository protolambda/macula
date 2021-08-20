from remerkleable.complex import Container, Vector, List
from remerkleable.byte_arrays import Bytes32, ByteVector
from remerkleable.basic import uint8, uint64, uint256, boolean


class Address(ByteVector[20]):
    pass


class BlockHistory(Vector[Bytes32, 256]):
    pass


# TODO: 64 MiB memory maximum enough or too much? Every 2x makes the tree a layer deeper,
# but otherwise not much cost for unused space
class Memory(List[uint8, 64 << 20]):
    pass


# EVM stack is max 1024 words
class Stack(List[Bytes32, 1024]):
    pass


# Needs to be as big as memory, all of it can be returned
class ReturnData(List[uint8, 64 << 20]):
    pass


# See https://github.com/ethereum/EIPs/blob/master/EIPS/eip-170.md
# ~24.5 KB
class Code(List[uint8, 0x6000]):
    pass


# Assuming a tx input can be max 400M gas, and 4 gas is paid per zero byte, then put a 100M limit on input.
class Input(List[uint8, 100_000_000]):
    pass


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
    difficulty: Bytes32
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
    value: Bytes32
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