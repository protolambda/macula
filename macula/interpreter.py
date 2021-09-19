from .trace import StepsTrace
from .step import *
from .exec_mode import *
from .jump_table import Operation, FRONTIER
from .call_work import call_work_proc
from .create_work import create_work_setup_proc, create_work_post_proc, create_work_revert_proc, create_work_err_proc
from .state_work import state_work_proc
from .mpt_work import mpt_work_proc
from .block import exec_pre_block, exec_block_pre_state_load, exec_block_history_load,\
    exec_block_calc_base_fee, exec_block_tx_loop, exec_post_block
from .tx import exec_tx_load

class Rules(object):
    ...  # TODO: some EIPs are activated only at certain block numbers


def rules(block_num: uint64) -> Rules:
    # TODO: no hardfork checks yet, just latest EVM spec only
    raise NotImplementedError


def operation_info(op: int, block_num: uint64) -> Operation:
    opcode = OpCode(op)
    # TODO: select opcode jump table based on block number, to support hard-forking
    return FRONTIER[opcode]


def next_step(trac: StepsTrace) -> Step:
    last = trac.last()
    mode = ExecMode(last.exec_mode)

    if mode == ExecMode.BlockPre:
        return exec_pre_block(trac)

    if mode == ExecMode.TxLoad:
        return exec_tx_load(trac)
    if mode == ExecMode.TxSig:
        raise NotImplementedError  # TODO signatures
    if mode == ExecMode.TxFeesPre:  # TODO validate fee stuff
        raise NotImplementedError
    if mode == ExecMode.TxFeesPost:  # TODO: charge tx fees
        raise NotImplementedError

    if mode == ExecMode.CallSetup:
        return call_work_proc(trac)
    if mode == ExecMode.CallPre:
        return exec_call_pre(trac)
    if mode == ExecMode.CallPost:
        return exec_call_post(trac)
    if mode == ExecMode.CallRevert:
        return exec_call_revert(trac)
    if ExecMode.ErrSTOP <= mode <= ExecMode.ErrInsufficientBalance:
        return exec_call_error(trac)

    if mode == ExecMode.CreateSetup:
        return create_work_setup_proc(trac)
    if mode == ExecMode.CreateInitPost:
        return create_work_post_proc(trac)
    if mode == ExecMode.CreateInitRevert:
        return create_work_revert_proc(trac)
    if mode == ExecMode.CreateInitErr:
        return create_work_err_proc(trac)

    # Interpreter loop consists of stack/memory/gas checks, and then opcode execution.
    if mode == ExecMode.OpcodeLoad:
        return exec_opcode_load(trac)
    if mode == ExecMode.ValidateStack:
        return exec_validate_stack(trac)
    if mode == ExecMode.ReadOnlyCheck:
        return exec_read_only_check(trac)
    if mode == ExecMode.ConstantGas:
        return exec_constant_gas(trac)
    if mode == ExecMode.CalcMemorySize:
        return exec_calc_memory_size(trac)
    if mode == ExecMode.DynamicGas:
        return exec_dynamic_gas(trac)
    if mode == ExecMode.UpdateMemorySize:
        return exec_update_memory_size(trac)
    if mode == ExecMode.OpcodeRun:
        return exec_opcode_run(trac)

    # TODO: if the block is invalid, then exit with generic FAIL? or DONE with error indication?
    if ExecMode.ErrInvalidTransactionType <= mode <= ExecMode.ErrInvalidTransactionSig:
        raise Exception("invalid block")

    if mode == ExecMode.StateWork:
        return state_work_proc(trac)
    if mode == ExecMode.MPTWork:
        return mpt_work_proc(trac)

    if mode == ExecMode.BlockPreStateLoad:
        return exec_block_pre_state_load(trac)
    if mode == ExecMode.BlockHistoryLoad:
        return exec_block_history_load(trac)
    if mode == ExecMode.BlockCalcBaseFee:
        return exec_block_calc_base_fee(trac)
    if mode == ExecMode.BlockTxLoop:
        return exec_block_tx_loop(trac)
    if mode == ExecMode.BlockPost:
        return exec_post_block(trac)

    raise ExecMode("unrecognized execution mode: %d" % mode)


def exec_call_pre(trac: StepsTrace) -> Step:
    # Call pre-processing
    last = trac.last()
    next = last.copy()

    # increment call depth
    call_depth = last.contract.call_depth
    next.contract.call_depth = call_depth + 1
    # reset return data, stack, memory, PC, and more
    # The caller must set the input-data and code.
    next.contract.ret_data = ReturnData()
    next.contract.stack = Stack()
    next.contract.memory = Memory()
    next.contract.pc = 0
    next.exec_mode = ExecMode.OpcodeLoad
    return next


def exec_call_post(trac: StepsTrace) -> Step:
    # note; call-depth will unwind itself, since we copy it from the parent.
    last = trac.last()
    parent_step = last.return_to_step.value()
    assert parent_step is not None
    next = parent_step.copy()
    # Next step is a lot like the parent, but we preserve the return data, return unused gas, and preserve the state
    # TODO maybe also track past log events, to reconstruct receipt root for block fraud proof
    next.state_root = last.state_root
    next.contract.ret_data = last.contract.ret_data
    next.contract.return_gas(last.contract.gas)
    next.contract.stack.push_u256(1)  # success

    if last.contract.is_init_code:
        next.exec_mode = ExecMode.CreateInitPost
    elif last.contract.call_depth <= 1:
        next.exec_mode = ExecMode.BlockTxSuccess
    else:
        # Continue processing in caller, exactly where we left of, next opcode
        next.exec_mode = ExecMode.OpcodeLoad
        next.contract.pc += 1

    return next


def exec_call_revert(trac: StepsTrace) -> Step:
    # note; call-depth will unwind itself, since we copy it from the parent.
    last = trac.last()
    parent_step = last.return_to_step.value()
    assert parent_step is not None
    next = parent_step.copy()
    # Next step is a lot like the parent, but we return gas,
    # set return data, and mark the error, without preserving state changes.
    next.contract.ret_data = last.contract.ret_data
    next.contract.return_gas(last.contract.gas)
    next.contract.stack.push_u256(0)  # fail

    if last.contract.is_init_code:
        next.exec_mode = ExecMode.CreateInitRevert
    elif last.contract.call_depth <= 1:
        next.exec_mode = ExecMode.BlockTxRevert
    else:
        # Continue processing in parent, exactly where we left of, next opcode
        next.exec_mode = ExecMode.OpcodeLoad
        next.contract.pc += 1

    return next


def exec_call_error(trac: StepsTrace) -> Step:
    # note; call-depth will unwind itself, since we copy it from the parent.
    last = trac.last()
    parent_step = last.return_to_step.value()
    assert parent_step is not None
    next = parent_step.copy()
    # This is an error, not a revert, so consume all gas: don't return any
    # And don't preserve the state-root changes, and don't return data

    # keep bubbling up the error, until we can mark the transaction as failed
    if last.contract.is_init_code:
        next.exec_mode = ExecMode.CreateInitErr
    elif last.contract.call_depth <= 1:
        next.exec_mode = ExecMode.BlockTxErr

    return next


def exec_opcode_load(trac: StepsTrace) -> Step:
    # To avoid reading the code every slot, we just cache the current opcode
    last = trac.last()
    next = last.copy()
    op = last.contract.code.get_op(last.contract.pc)
    next.contract.op = op.byte()
    next.exec_mode = ExecMode.ValidateStack
    return next


def exec_validate_stack(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    stack_len = len(last.contract.stack)
    operation = operation_info(last.contract.op, last.block.block_number)
    # ensure there are enough stack items available to perform the operation
    if stack_len < operation.min_stack:
        next.exec_mode = ExecMode.ErrStackUnderflow
        return next
    elif stack_len > operation.max_stack:
        next.exec_mode = ExecMode.ErrStackOverflow
        return next
    else:
        # valid stack, bless. Continue interpreter
        next.exec_mode = ExecMode.ReadOnlyCheck
        return next


def exec_read_only_check(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    # If the interpreter is operating in readonly mode, make sure no
    # state-modifying operation is performed. The 3rd stack item
    # for a call operation is the value. Transferring value from one
    # account to the others means the state is modified and should also
    # return with an error.
    if last.contract.read_only:
        op = last.contract.op
        operation = operation_info(last.contract.op, last.block.block_number)
        if operation.writes:
            next.exec_mode = ExecMode.ErrWriteProtection
            return next
        if op == OpCode.CALL:
            value = last.contract.stack.back_b32(2)
            if value != Bytes32():
                next.exec_mode = ExecMode.ErrWriteProtection
                return next
    # All OK, continue to next step
    next.exec_mode = ExecMode.ConstantGas
    return next


def exec_constant_gas(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    operation = operation_info(last.contract.op, last.block.block_number)
    # Static portion of gas
    if not next.contract.use_gas(operation.constant_gas):
        next.exec_mode = ExecMode.ErrOutOfGas
        return next
    # Continue interpreter to next step
    next.exec_mode = ExecMode.CalcMemorySize
    return next


def exec_calc_memory_size(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    operation = operation_info(last.contract.op, last.block.block_number)
    memory_size = 0
    # calculate the new memory size and expand the memory to fit
    # the operation
    # Memory check needs to be done prior to evaluating the dynamic gas portion,
    # to detect calculation overflows
    if operation.memory_size is not None:
        mem_op, overflow = operation.memory_size(last.contract.stack)
        if overflow:
            next.exec_mode = ExecMode.ErrGasUintOverflow
            return next
        # memory is expanded in words of 32 bytes. Gas is also calculated in words.
        memory_size = int(to_word_size(mem_op)) * 32
        if memory_size >= 1 << 64:
            next.exec_mode = ExecMode.ErrGasUintOverflow
            return next

    next.contract.memory_desired = memory_size
    next.exec_mode = ExecMode.DynamicGas
    return next


def exec_dynamic_gas(trac: StepsTrace) -> Step:
    last = trac.last()
    operation = operation_info(last.contract.op, last.block.block_number)
    if operation.dynamic_gas is not None:
        # Dynamic gas is complex, it steals the step to deal with it,
        # and optionally require more steps before interpreter continuation
        return operation.dynamic_gas(trac)
    else:
        next = last.copy()
        next.exec_mode = ExecMode.UpdateMemorySize
        return next


def exec_update_memory_size(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    memory_size = last.contract.memory_desired
    m_length = len(next.contract.memory)
    if m_length >= memory_size:
        # no extension to do
        next.exec_mode = ExecMode.OpcodeRun
        return next
    # If we can efficiently add 32 bytes of memory, go for it.
    # Otherwise just align by adding a byte, or finishing trailing non-aligning bytes.
    if (memory_size-m_length >= 32) and (m_length % 32 == 0):
        memory_size += 32
        next.contract.memory.append_zero_32_bytes()
    else:
        memory_size += 1
        next.contract.memory.append(uint8(0))

    # check if we can exit the memory extension step repeat already
    if len(next.contract.memory) >= memory_size:
        # no extension to do
        next.exec_mode = ExecMode.OpcodeRun
        return next
    else:
        # leave the execution mode on ExecMode.UpdateMemorySize.
        # The next step will further extend the memory size.
        return next


def exec_opcode_run(trac: StepsTrace) -> Step:
    # when done running, continue with ExecOpcodeLoad. Or any error
    last = trac.last()
    operation = operation_info(last.contract.op, last.block.block_number)
    return operation.proc(trac)


def to_word_size(size: uint64) -> uint64:
    if size > (((1 << 64) - 1) - 31):
        return (((1 << 64) - 1) // 32) + 1
    return (size + 31) // 32
