from .trace import StepsTrace
from .step import *
from .exec_mode import *
from .jump_table import Operation, FRONTIER


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
        raise NotImplementedError  # TODO block init work
    if mode == ExecMode.TxInclusion:
        raise NotImplementedError  # TODO: check transaction is included, check fee params, signature validity, etc.
    if mode == ExecMode.TxSig:
        raise NotImplementedError  # TODO signatures
    if mode == ExecMode.TxFeesPre:  # TODO validate fee stuff
        raise NotImplementedError
    if mode == ExecMode.TxFeesPost:  # TODO: charge tx fees
        raise NotImplementedError

    if mode == ExecMode.CallPre:
        return exec_call_pre(trac)
    if mode == ExecMode.CallPost:
        return exec_call_post(trac)

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

    if exec_mode_err_range[0] <= mode.value <= exec_mode_err_range[1]:
        return exec_error(trac)


def exec_call_pre(trac: StepsTrace) -> Step:
    # Call pre-processing
    last = trac.last()
    next = last.copy()

    # increment call depth
    call_depth = last.call_depth
    next.call_depth = call_depth + 1
    # reset return data, stack, memory, PC, and more
    # The caller must set the input-data and code.
    next.ret_data = ReturnData()
    next.stack = Stack()
    next.memory = Memory()
    next.pc = 0
    next.exec_mode = ExecMode.OpcodeLoad.value
    return next


def exec_call_post(trac: StepsTrace) -> Step:
    # note; call-depth will unwind itself, since we copy it from the caller.
    last = trac.last()
    caller_step = trac.by_root(last.return_to_step)
    next = caller_step.copy()
    # Next step is a lot like the caller, but we preserve the return data, return unused gas, and preserve the state
    # TODO maybe also track past log events, to reconstruct receipt root for block fraud proof
    next.state_root = last.state_root
    next.ret_data = last.ret_data
    next.return_gas(last.gas)

    # Continue processing in caller, exactly where we left of, next opcode
    next.exec_mode = ExecMode.OpcodeLoad.value
    return next


def exec_opcode_load(trac: StepsTrace) -> Step:
    # To avoid reading the code every slot, we just cache the current opcode
    last = trac.last()
    next = last.copy()
    op = last.code.get_op(last.pc)
    next.op = op.byte()
    next.exec_mode = ExecMode.ValidateStack.value
    return next


def exec_validate_stack(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    stack_len = len(last.stack)
    operation = operation_info(last.op, last.block_number)
    # ensure there are enough stack items available to perform the operation
    if stack_len < operation.min_stack:
        next.exec_mode = ExecMode.ErrStackUnderflow.value
        return next
    elif stack_len > operation.max_stack:
        next.exec_mode = ExecMode.ErrStackOverflow.value
        return next
    else:
        # valid stack, bless. Continue interpreter
        next.exec_mode = ExecMode.ReadOnlyCheck.value
        return next


def exec_read_only_check(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    # If the interpreter is operating in readonly mode, make sure no
    # state-modifying operation is performed. The 3rd stack item
    # for a call operation is the value. Transferring value from one
    # account to the others means the state is modified and should also
    # return with an error.
    if last.read_only:
        op = last.op
        operation = operation_info(last.op, last.block_number)
        if operation.writes:
            next.exec_mode = ExecMode.ErrWriteProtection.value
            return next
        if op == OpCode.CALL:
            value = last.stack.back_b32(2)
            if value != Bytes32():
                next.exec_mode = ExecMode.ErrWriteProtection.value
                return next
    # All OK, continue to next step
    next.exec_mode = ExecMode.ConstantGas.value
    return next


def exec_constant_gas(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    operation = operation_info(last.op, last.block_number)
    # Static portion of gas
    if not next.use_gas(operation.constant_gas):
        next.exec_mode = ExecMode.ErrOutOfGas.value
        return next
    # Continue interpreter to next step
    next.exec_mode = ExecMode.CalcMemorySize.value
    return next


def exec_calc_memory_size(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    operation = operation_info(last.op, last.block_number)
    memory_size = 0
    # calculate the new memory size and expand the memory to fit
    # the operation
    # Memory check needs to be done prior to evaluating the dynamic gas portion,
    # to detect calculation overflows
    if operation.memory_size is not None:
        mem_op, overflow = operation.memory_size(last.stack)
        if overflow:
            next.exec_mode = ExecMode.ErrGasUintOverflow.value
            return next
        # memory is expanded in words of 32 bytes. Gas is also calculated in words.
        memory_size = int(to_word_size(mem_op)) * 32
        if memory_size >= 1 << 64:
            next.exec_mode = ExecMode.ErrGasUintOverflow.value
            return next

    next.memory_desired = memory_size
    next.exec_mode = ExecMode.DynamicGas.value
    return next


def exec_dynamic_gas(trac: StepsTrace) -> Step:
    last = trac.last()
    operation = operation_info(last.op, last.block_number)
    if operation.dynamic_gas is not None:
        # Dynamic gas is complex, it steals the step to deal with it,
        # and optionally require more steps before interpreter continuation
        return operation.dynamic_gas(trac)
    else:
        next = last.copy()
        next.exec_mode = ExecMode.UpdateMemorySize.value
        return next


def exec_update_memory_size(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    memory_size = last.memory_desired
    m_length = len(next.memory)
    if m_length >= memory_size:
        # no extension to do
        next.exec_mode = ExecMode.OpcodeRun.value
        return next
    # If we can efficiently add 32 bytes of memory, go for it.
    # Otherwise just align by adding a byte, or finishing trailing non-aligning bytes.
    if (memory_size-m_length >= 32) and (m_length % 32 == 0):
        memory_size += 32
        next.memory.append_zero_32_bytes()
    else:
        memory_size += 1
        next.memory.append(uint8(0))

    # check if we can exit the memory extension step repeat already
    if len(next.memory) >= memory_size:
        # no extension to do
        next.exec_mode = ExecMode.OpcodeRun.value
        return next
    else:
        # leave the execution mode on ExecMode.UpdateMemorySize.
        # The next step will further extend the memory size.
        return next


def exec_opcode_run(trac: StepsTrace) -> Step:
    # when done running, continue with ExecOpcodeLoad. Or any error
    last = trac.last()
    operation = operation_info(last.op, last.block_number)
    return operation.proc(trac)


def exec_error(trac: StepsTrace) -> Step:
    # Stops execution
    #
    # Any error should follow up with running call-post processing
    last = trac.last()
    next = last.copy()
    # if not a natural revert, then consume all gas.
    if last.exec_mode != ExecMode.ErrExecutionReverted.value:
        next.gas = 0

    # TODO: if a revert, then complete the call (without preserving state-root),
    #  preserve consumed gas, and return data

    # TODO: if not a revert, but an actual error,
    #  then halt the interpreter and mark the tx as failed.
    raise NotImplementedError


def to_word_size(size: uint64) -> uint64:
    if size > (((1 << 64) - 1) - 31):
        return (((1 << 64) - 1) // 32) + 1
    return (size + 31) // 32
