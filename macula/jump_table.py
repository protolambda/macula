from typing import Optional, Callable, Tuple
from .instructions import *
from .stack_table import *
from .gas import *
from .gas_table import *
from .memory_table import *

MemoryCalculator = Callable[[Stack], Tuple[uint64, bool]]


class Operation(object):
    proc: Processor
    constant_gas: uint64
    # dynamic gas has its whole own step to produce
    dynamic_gas: Optional[Processor]
    min_stack: uint64
    max_stack: uint64
    # stack -> size, overflow flag
    memory_size: Optional[MemoryCalculator]

    def __init__(self,
                 proc: Processor,
                 constant_gas=0,
                 dynamic_gas=None,
                 min_stack=0,
                 max_stack=0,
                 memory_size=None):
        self.proc = proc
        self.constant_gas = uint64(constant_gas)
        self.dynamic_gas = dynamic_gas
        self.min_stack = uint64(min_stack)
        self.max_stack = uint64(max_stack)
        self.memory_size = memory_size


FRONTIER = {
    OpCode.STOP: Operation(
        proc=op_stop,
        constant_gas=uint64(0),
        min_stack=min_stack(0, 0),
        max_stack=max_stack(0, 0),
        # halting property is part of the processing.
    ),
    OpCode.ADD: Operation(
        proc=op_add,
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_stack(2, 1),
        max_stack=max_stack(2, 1),
    ),
    OpCode.MUL: Operation(
        proc=op_mul,
        constant_gas=GAS_FAST_STEP,
        min_stack=min_stack(2, 1),
        max_stack=max_stack(2, 1),
    ),
    OpCode.SUB: Operation(
        proc=op_sub,
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_stack(2, 1),
        max_stack=max_stack(2, 1),
    ),
    OpCode.DIV: Operation(
        proc=op_div,
        constant_gas=GAS_FAST_STEP,
        min_stack=min_stack(2, 1),
        max_stack=max_stack(2, 1),
    ),
    OpCode.SDIV: Operation(
        proc=op_sdiv,
        constant_gas=GAS_FAST_STEP,
        min_stack=min_stack(2, 1),
        max_stack=max_stack(2, 1),
    ),
    OpCode.MOD: Operation(
        proc=op_mod,
        constant_gas=GAS_FAST_STEP,
        min_stack=min_stack(2, 1),
        max_stack=max_stack(2, 1),
    ),
    OpCode.SMOD: Operation(
        proc=op_smod,
        constant_gas=GAS_FAST_STEP,
        min_stack=min_stack(2, 1),
        max_stack=max_stack(2, 1),
    ),
    OpCode.ADDMOD: Operation(
        proc=op_addmod,
        constant_gas=GAS_MID_STEP,
        min_stack=min_stack(3, 1),
        max_stack=max_stack(3, 1),
    ),
    OpCode.MULMOD: Operation(
        proc=op_mulmod,
        constant_gas=GAS_MID_STEP,
        min_stack=min_stack(3, 1),
        max_stack=max_stack(3, 1),
    ),
    OpCode.EXP: Operation(
        proc=op_exp,
        dynamic_gas=gas_exp_frontier,
        min_stack=min_stack(2, 1),
        max_stack=max_stack(2, 1),
    ),
    OpCode.SIGNEXTEND: Operation(
        proc=op_sign_extend,
        constant_gas=GAS_FAST_STEP,
        min_stack=min_stack(2, 1),
        max_stack=max_stack(2, 1),
    ),
    OpCode.LT: Operation(
        proc=op_lt,
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_stack(2, 1),
        max_stack=max_stack(2, 1),
    ),
    OpCode.GT: Operation(
        proc=op_gt,
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_stack(2, 1),
        max_stack=max_stack(2, 1),
    ),
    OpCode.SLT: Operation(
        proc=op_slt,
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_stack(2, 1),
        max_stack=max_stack(2, 1),
    ),
    OpCode.SGT: Operation(
        proc=op_sgt,
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_stack(2, 1),
        max_stack=max_stack(2, 1),
    ),
    OpCode.EQ: Operation(
        proc=op_eq,
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_stack(2, 1),
        max_stack=max_stack(2, 1),
    ),
    OpCode.ISZERO: Operation(
        proc=op_iszero,
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_stack(1, 1),
        max_stack=max_stack(1, 1),
    ),
    OpCode.AND: Operation(
        proc=op_and,
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_stack(2, 1),
        max_stack=max_stack(2, 1),
    ),
    OpCode.XOR: Operation(
        proc=op_xor,
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_stack(2, 1),
        max_stack=max_stack(2, 1),
    ),
    OpCode.OR: Operation(
        proc=op_or,
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_stack(2, 1),
        max_stack=max_stack(2, 1),
    ),
    OpCode.NOT: Operation(
        proc=op_not,
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_stack(1, 1),
        max_stack=max_stack(1, 1),
    ),
    OpCode.BYTE: Operation(
        proc=op_byte,
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_stack(2, 1),
        max_stack=max_stack(2, 1),
    ),
    OpCode.SHA3: Operation(
        proc=op_sha3,
        constant_gas=params.Sha3Gas,
        dynamic_gas=gas_sha3,
        min_stack=min_stack(2, 1),
        max_stack=max_stack(2, 1),
        memory_size=memory_sha3,
    ),
    OpCode.ADDRESS: Operation(
        proc=op_address,
        constant_gas=GAS_QUICK_STEP,
        min_stack=min_stack(0, 1),
        max_stack=max_stack(0, 1),
    ),
    OpCode.BALANCE: Operation(
        proc=op_balance,
        constant_gas=params.BalanceGasFrontier,
        min_stack=min_stack(1, 1),
        max_stack=max_stack(1, 1),
    ),
    OpCode.ORIGIN: Operation(
        proc=op_origin,
        constant_gas=GAS_QUICK_STEP,
        min_stack=min_stack(0, 1),
        max_stack=max_stack(0, 1),
    ),
    OpCode.CALLER: Operation(
        proc=op_caller,
        constant_gas=GAS_QUICK_STEP,
        min_stack=min_stack(0, 1),
        max_stack=max_stack(0, 1),
    ),
    OpCode.CALLVALUE: Operation(
        proc=op_call_value,
        constant_gas=GAS_QUICK_STEP,
        min_stack=min_stack(0, 1),
        max_stack=max_stack(0, 1),
    ),
    OpCode.CALLDATALOAD: Operation(
        proc=op_call_data_load,
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_stack(1, 1),
        max_stack=max_stack(1, 1),
    ),
    OpCode.CALLDATASIZE: Operation(
        proc=op_call_data_size,
        constant_gas=GAS_QUICK_STEP,
        min_stack=min_stack(0, 1),
        max_stack=max_stack(0, 1),
    ),
    OpCode.CALLDATACOPY: Operation(
        proc=op_call_data_copy,
        constant_gas=GAS_FASTEST_STEP,
        dynamic_gas=gas_call_data_copy,
        min_stack=min_stack(3, 0),
        max_stack=max_stack(3, 0),
        memory_size=memory_call_data_copy,
    ),
    OpCode.CODESIZE: Operation(
        proc=op_code_size,
        constant_gas=GAS_QUICK_STEP,
        min_stack=min_stack(0, 1),
        max_stack=max_stack(0, 1),
    ),
    OpCode.CODECOPY: Operation(
        proc=op_code_copy,
        constant_gas=GAS_FASTEST_STEP,
        dynamic_gas=gas_code_copy,
        min_stack=min_stack(3, 0),
        max_stack=max_stack(3, 0),
        memory_size=memory_code_copy,
    ),
    OpCode.GASPRICE: Operation(
        proc=op_gas_price,
        constant_gas=GAS_QUICK_STEP,
        min_stack=min_stack(0, 1),
        max_stack=max_stack(0, 1),
    ),
    OpCode.EXTCODESIZE: Operation(
        proc=op_ext_code_size,
        constant_gas=params.ExtcodeSizeGasFrontier,
        min_stack=min_stack(1, 1),
        max_stack=max_stack(1, 1),
    ),
    OpCode.EXTCODECOPY: Operation(
        proc=op_ext_code_copy,
        constant_gas=params.ExtcodeCopyBaseFrontier,
        dynamic_gas=gas_ext_code_copy,
        min_stack=min_stack(4, 0),
        max_stack=max_stack(4, 0),
        memory_size=memory_ext_code_copy,
    ),
    OpCode.BLOCKHASH: Operation(
        proc=op_block_hash,
        constant_gas=GAS_EXT_STEP,
        min_stack=min_stack(1, 1),
        max_stack=max_stack(1, 1),
    ),
    OpCode.COINBASE: Operation(
        proc=op_coinbase,
        constant_gas=GAS_QUICK_STEP,
        min_stack=min_stack(0, 1),
        max_stack=max_stack(0, 1),
    ),
    OpCode.TIMESTAMP: Operation(
        proc=op_timestamp,
        constant_gas=GAS_QUICK_STEP,
        min_stack=min_stack(0, 1),
        max_stack=max_stack(0, 1),
    ),
    OpCode.NUMBER: Operation(
        proc=op_number,
        constant_gas=GAS_QUICK_STEP,
        min_stack=min_stack(0, 1),
        max_stack=max_stack(0, 1),
    ),
    OpCode.DIFFICULTY: Operation(
        proc=op_difficulty,
        constant_gas=GAS_QUICK_STEP,
        min_stack=min_stack(0, 1),
        max_stack=max_stack(0, 1),
    ),
    OpCode.GASLIMIT: Operation(
        proc=op_gas_limit,
        constant_gas=GAS_QUICK_STEP,
        min_stack=min_stack(0, 1),
        max_stack=max_stack(0, 1),
    ),
    OpCode.POP: Operation(
        proc=op_pop,
        constant_gas=GAS_QUICK_STEP,
        min_stack=min_stack(1, 0),
        max_stack=max_stack(1, 0),
    ),
    OpCode.MLOAD: Operation(
        proc=op_mload,
        constant_gas=GAS_FASTEST_STEP,
        dynamic_gas=gas_mload,
        min_stack=min_stack(1, 1),
        max_stack=max_stack(1, 1),
        memory_size=memory_mload,
    ),
    OpCode.MSTORE: Operation(
        proc=op_mstore,
        constant_gas=GAS_FASTEST_STEP,
        dynamic_gas=gas_mstore,
        min_stack=min_stack(2, 0),
        max_stack=max_stack(2, 0),
        memory_size=memory_mstore,
    ),
    OpCode.MSTORE8: Operation(
        proc=op_mstore8,
        constant_gas=GAS_FASTEST_STEP,
        dynamic_gas=gas_mstore8,
        memory_size=memory_mstore8,
        min_stack=min_stack(2, 0),
        max_stack=max_stack(2, 0),
    ),
    OpCode.SLOAD: Operation(
        proc=op_sload,
        constant_gas=params.SloadGasFrontier,
        min_stack=min_stack(1, 1),
        max_stack=max_stack(1, 1),
    ),
    OpCode.SSTORE: Operation(
        proc=op_sstore,
        dynamic_gas=gas_sstore,
        min_stack=min_stack(2, 0),
        max_stack=max_stack(2, 0),
        # writes=true,
    ),
    OpCode.JUMP: Operation(
        proc=op_jump,
        constant_gas=GAS_MID_STEP,
        min_stack=min_stack(1, 0),
        max_stack=max_stack(1, 0),
        # jumps=true,
    ),
    OpCode.JUMPI: Operation(
        proc=op_jumpi,
        constant_gas=GAS_SLOW_STEP,
        min_stack=min_stack(2, 0),
        max_stack=max_stack(2, 0),
        # jumps=true,
    ),
    OpCode.PC: Operation(
        proc=op_pc,
        constant_gas=GAS_QUICK_STEP,
        min_stack=min_stack(0, 1),
        max_stack=max_stack(0, 1),
    ),
    OpCode.MSIZE: Operation(
        proc=op_msize,
        constant_gas=GAS_QUICK_STEP,
        min_stack=min_stack(0, 1),
        max_stack=max_stack(0, 1),
    ),
    OpCode.GAS: Operation(
        proc=op_gas,
        constant_gas=GAS_QUICK_STEP,
        min_stack=min_stack(0, 1),
        max_stack=max_stack(0, 1),
    ),
    OpCode.JUMPDEST: Operation(
        proc=op_jump_dest,
        constant_gas=params.JumpdestGas,
        min_stack=min_stack(0, 0),
        max_stack=max_stack(0, 0),
    ),
    OpCode.PUSH1: Operation(
        proc=op_push1,
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_stack(0, 1),
        max_stack=max_stack(0, 1),
    ),
    OpCode.PUSH2: Operation(
        proc=make_push(2, 2),
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_stack(0, 1),
        max_stack=max_stack(0, 1),
    ),
    OpCode.PUSH3: Operation(
        proc=make_push(3, 3),
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_stack(0, 1),
        max_stack=max_stack(0, 1),
    ),
    OpCode.PUSH4: Operation(
        proc=make_push(4, 4),
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_stack(0, 1),
        max_stack=max_stack(0, 1),
    ),
    OpCode.PUSH5: Operation(
        proc=make_push(5, 5),
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_stack(0, 1),
        max_stack=max_stack(0, 1),
    ),
    OpCode.PUSH6: Operation(
        proc=make_push(6, 6),
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_stack(0, 1),
        max_stack=max_stack(0, 1),
    ),
    OpCode.PUSH7: Operation(
        proc=make_push(7, 7),
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_stack(0, 1),
        max_stack=max_stack(0, 1),
    ),
    OpCode.PUSH8: Operation(
        proc=make_push(8, 8),
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_stack(0, 1),
        max_stack=max_stack(0, 1),
    ),
    OpCode.PUSH9: Operation(
        proc=make_push(9, 9),
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_stack(0, 1),
        max_stack=max_stack(0, 1),
    ),
    OpCode.PUSH10: Operation(
        proc=make_push(10, 10),
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_stack(0, 1),
        max_stack=max_stack(0, 1),
    ),
    OpCode.PUSH11: Operation(
        proc=make_push(11, 11),
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_stack(0, 1),
        max_stack=max_stack(0, 1),
    ),
    OpCode.PUSH12: Operation(
        proc=make_push(12, 12),
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_stack(0, 1),
        max_stack=max_stack(0, 1),
    ),
    OpCode.PUSH13: Operation(
        proc=make_push(13, 13),
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_stack(0, 1),
        max_stack=max_stack(0, 1),
    ),
    OpCode.PUSH14: Operation(
        proc=make_push(14, 14),
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_stack(0, 1),
        max_stack=max_stack(0, 1),
    ),
    OpCode.PUSH15: Operation(
        proc=make_push(15, 15),
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_stack(0, 1),
        max_stack=max_stack(0, 1),
    ),
    OpCode.PUSH16: Operation(
        proc=make_push(16, 16),
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_stack(0, 1),
        max_stack=max_stack(0, 1),
    ),
    OpCode.PUSH17: Operation(
        proc=make_push(17, 17),
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_stack(0, 1),
        max_stack=max_stack(0, 1),
    ),
    OpCode.PUSH18: Operation(
        proc=make_push(18, 18),
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_stack(0, 1),
        max_stack=max_stack(0, 1),
    ),
    OpCode.PUSH19: Operation(
        proc=make_push(19, 19),
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_stack(0, 1),
        max_stack=max_stack(0, 1),
    ),
    OpCode.PUSH20: Operation(
        proc=make_push(20, 20),
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_stack(0, 1),
        max_stack=max_stack(0, 1),
    ),
    OpCode.PUSH21: Operation(
        proc=make_push(21, 21),
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_stack(0, 1),
        max_stack=max_stack(0, 1),
    ),
    OpCode.PUSH22: Operation(
        proc=make_push(22, 22),
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_stack(0, 1),
        max_stack=max_stack(0, 1),
    ),
    OpCode.PUSH23: Operation(
        proc=make_push(23, 23),
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_stack(0, 1),
        max_stack=max_stack(0, 1),
    ),
    OpCode.PUSH24: Operation(
        proc=make_push(24, 24),
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_stack(0, 1),
        max_stack=max_stack(0, 1),
    ),
    OpCode.PUSH25: Operation(
        proc=make_push(25, 25),
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_stack(0, 1),
        max_stack=max_stack(0, 1),
    ),
    OpCode.PUSH26: Operation(
        proc=make_push(26, 26),
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_stack(0, 1),
        max_stack=max_stack(0, 1),
    ),
    OpCode.PUSH27: Operation(
        proc=make_push(27, 27),
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_stack(0, 1),
        max_stack=max_stack(0, 1),
    ),
    OpCode.PUSH28: Operation(
        proc=make_push(28, 28),
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_stack(0, 1),
        max_stack=max_stack(0, 1),
    ),
    OpCode.PUSH29: Operation(
        proc=make_push(29, 29),
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_stack(0, 1),
        max_stack=max_stack(0, 1),
    ),
    OpCode.PUSH30: Operation(
        proc=make_push(30, 30),
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_stack(0, 1),
        max_stack=max_stack(0, 1),
    ),
    OpCode.PUSH31: Operation(
        proc=make_push(31, 31),
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_stack(0, 1),
        max_stack=max_stack(0, 1),
    ),
    OpCode.PUSH32: Operation(
        proc=make_push(32, 32),
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_stack(0, 1),
        max_stack=max_stack(0, 1),
    ),
    OpCode.DUP1: Operation(
        proc=make_dup(1),
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_dup_stack(1),
        max_stack=max_dup_stack(1),
    ),
    OpCode.DUP2: Operation(
        proc=make_dup(2),
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_dup_stack(2),
        max_stack=max_dup_stack(2),
    ),
    OpCode.DUP3: Operation(
        proc=make_dup(3),
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_dup_stack(3),
        max_stack=max_dup_stack(3),
    ),
    OpCode.DUP4: Operation(
        proc=make_dup(4),
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_dup_stack(4),
        max_stack=max_dup_stack(4),
    ),
    OpCode.DUP5: Operation(
        proc=make_dup(5),
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_dup_stack(5),
        max_stack=max_dup_stack(5),
    ),
    OpCode.DUP6: Operation(
        proc=make_dup(6),
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_dup_stack(6),
        max_stack=max_dup_stack(6),
    ),
    OpCode.DUP7: Operation(
        proc=make_dup(7),
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_dup_stack(7),
        max_stack=max_dup_stack(7),
    ),
    OpCode.DUP8: Operation(
        proc=make_dup(8),
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_dup_stack(8),
        max_stack=max_dup_stack(8),
    ),
    OpCode.DUP9: Operation(
        proc=make_dup(9),
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_dup_stack(9),
        max_stack=max_dup_stack(9),
    ),
    OpCode.DUP10: Operation(
        proc=make_dup(10),
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_dup_stack(10),
        max_stack=max_dup_stack(10),
    ),
    OpCode.DUP11: Operation(
        proc=make_dup(11),
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_dup_stack(11),
        max_stack=max_dup_stack(11),
    ),
    OpCode.DUP12: Operation(
        proc=make_dup(12),
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_dup_stack(12),
        max_stack=max_dup_stack(12),
    ),
    OpCode.DUP13: Operation(
        proc=make_dup(13),
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_dup_stack(13),
        max_stack=max_dup_stack(13),
    ),
    OpCode.DUP14: Operation(
        proc=make_dup(14),
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_dup_stack(14),
        max_stack=max_dup_stack(14),
    ),
    OpCode.DUP15: Operation(
        proc=make_dup(15),
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_dup_stack(15),
        max_stack=max_dup_stack(15),
    ),
    OpCode.DUP16: Operation(
        proc=make_dup(16),
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_dup_stack(16),
        max_stack=max_dup_stack(16),
    ),
    OpCode.SWAP1: Operation(
        proc=make_swap(1),
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_swap_stack(2),
        max_stack=max_swap_stack(2),
    ),
    OpCode.SWAP2: Operation(
        proc=make_swap(2),
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_swap_stack(3),
        max_stack=max_swap_stack(3),
    ),
    OpCode.SWAP3: Operation(
        proc=make_swap(3),
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_swap_stack(4),
        max_stack=max_swap_stack(4),
    ),
    OpCode.SWAP4: Operation(
        proc=make_swap(4),
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_swap_stack(5),
        max_stack=max_swap_stack(5),
    ),
    OpCode.SWAP5: Operation(
        proc=make_swap(5),
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_swap_stack(6),
        max_stack=max_swap_stack(6),
    ),
    OpCode.SWAP6: Operation(
        proc=make_swap(6),
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_swap_stack(7),
        max_stack=max_swap_stack(7),
    ),
    OpCode.SWAP7: Operation(
        proc=make_swap(7),
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_swap_stack(8),
        max_stack=max_swap_stack(8),
    ),
    OpCode.SWAP8: Operation(
        proc=make_swap(8),
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_swap_stack(9),
        max_stack=max_swap_stack(9),
    ),
    OpCode.SWAP9: Operation(
        proc=make_swap(9),
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_swap_stack(10),
        max_stack=max_swap_stack(10),
    ),
    OpCode.SWAP10: Operation(
        proc=make_swap(10),
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_swap_stack(11),
        max_stack=max_swap_stack(11),
    ),
    OpCode.SWAP11: Operation(
        proc=make_swap(11),
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_swap_stack(12),
        max_stack=max_swap_stack(12),
    ),
    OpCode.SWAP12: Operation(
        proc=make_swap(12),
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_swap_stack(13),
        max_stack=max_swap_stack(13),
    ),
    OpCode.SWAP13: Operation(
        proc=make_swap(13),
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_swap_stack(14),
        max_stack=max_swap_stack(14),
    ),
    OpCode.SWAP14: Operation(
        proc=make_swap(14),
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_swap_stack(15),
        max_stack=max_swap_stack(15),
    ),
    OpCode.SWAP15: Operation(
        proc=make_swap(15),
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_swap_stack(16),
        max_stack=max_swap_stack(16),
    ),
    OpCode.SWAP16: Operation(
        proc=make_swap(16),
        constant_gas=GAS_FASTEST_STEP,
        min_stack=min_swap_stack(17),
        max_stack=max_swap_stack(17),
    ),
    OpCode.LOG0: Operation(
        proc=make_log(0),
        dynamic_gas=make_gas_log(0),
        min_stack=min_stack(2, 0),
        max_stack=max_stack(2, 0),
        memory_size=memory_log,
        # writes=true,
    ),
    OpCode.LOG1: Operation(
        proc=make_log(1),
        dynamic_gas=make_gas_log(1),
        min_stack=min_stack(3, 0),
        max_stack=max_stack(3, 0),
        memory_size=memory_log,
        # writes=true,
    ),
    OpCode.LOG2: Operation(
        proc=make_log(2),
        dynamic_gas=make_gas_log(2),
        min_stack=min_stack(4, 0),
        max_stack=max_stack(4, 0),
        memory_size=memory_log,
        # writes=true,
    ),
    OpCode.LOG3: Operation(
        proc=make_log(3),
        dynamic_gas=make_gas_log(3),
        min_stack=min_stack(5, 0),
        max_stack=max_stack(5, 0),
        memory_size=memory_log,
        # writes=true,
    ),
    OpCode.LOG4: Operation(
        proc=make_log(4),
        dynamic_gas=make_gas_log(4),
        min_stack=min_stack(6, 0),
        max_stack=max_stack(6, 0),
        memory_size=memory_log,
        # writes=true,
    ),
    OpCode.CREATE: Operation(
        proc=op_create,
        constant_gas=params.CreateGas,
        dynamic_gas=gas_create,
        min_stack=min_stack(3, 1),
        max_stack=max_stack(3, 1),
        memory_size=memory_create,
        # writes=true,
        # returns=true,
    ),
    OpCode.CALL: Operation(
        proc=op_call,
        constant_gas=params.CallGasFrontier,
        dynamic_gas=gas_call,
        min_stack=min_stack(7, 1),
        max_stack=max_stack(7, 1),
        memory_size=memory_call,
        # returns=true,
    ),
    OpCode.CALLCODE: Operation(
        proc=op_callCode,
        constant_gas=params.CallGasFrontier,
        dynamic_gas=gas_call_code,
        min_stack=min_stack(7, 1),
        max_stack=max_stack(7, 1),
        memory_size=memory_call,
        # returns=true,
    ),
    OpCode.RETURN: Operation(
        proc=op_return,
        dynamic_gas=gas_return,
        min_stack=min_stack(2, 0),
        max_stack=max_stack(2, 0),
        memory_size=memory_return,
        # halts=true,
    ),
    OpCode.SELFDESTRUCT: Operation(
        proc=op_self_destruct,
        dynamic_gas=gas_self_destruct,
        min_stack=min_stack(1, 0),
        max_stack=max_stack(1, 0),
        # halts=true,
        # writes=true,
    )
}

HOMESTEAD = {
    **FRONTIER,
    OpCode.DELEGATECALL: Operation(
        proc=op_delegate_call,
        dynamic_gas=gas_delegate_call,
        constant_gas=params.CallGasFrontier,
        min_stack=min_stack(6, 1),
        max_stack=max_stack(6, 1),
        memory_size=memory_delegate_call,
        # returns:     true,
    )
}

TANGERINE_WHISTLE = {
    **HOMESTEAD,
    # TODO
}

SPURIOUS_DRAGON = {
    **TANGERINE_WHISTLE,
    # TODO
}

BYZANTIUM = {
    **SPURIOUS_DRAGON,
    # TODO
}

CONSTANTINOPLE = {
    **BYZANTIUM,
    # TODO
}

ISTANBUL = {
    **CONSTANTINOPLE,
    # TODO
}

BERLIN = {
    **ISTANBUL,
    # TODO
}

LONDON = {
    **BERLIN,
    # TODO
}
