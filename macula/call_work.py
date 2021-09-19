from enum import IntEnum
from .step import Step, Input
from .trace import StepsTrace
from .exec_mode import ExecMode
from .params import CALL_CREATE_DEPTH


class CallMode(IntEnum):
    START = 0x00
    LOAD_SCOPE = 0x01
    RESET_INPUT = 0x02
    LOAD_INPUT = 0x03
    CALL_DEPTH_CHECK = 0x04
    READ_BALANCE = 0x05
    CHECK_TRANSFER_VALUE = 0x06
    CHECK_ACCOUNT_EXISTS = 0x07
    CHECK_IF_PRECOMPILE = 0x08
    # if the account didn't exist yet
    CREATE_TO_ACCOUNT = 0x09
    TRANSFER_VALUE = 0x0a
    LOAD_CODE = 0x0b  # branches into appropriate type of contract load
    LOAD_PRECOMPILE = 0x0c
    LOAD_REGULAR_CONTRACT_CODE_HASH = 0x0d
    LOAD_REGULAR_CONTRACT_CODE = 0x0e
    CHECK_RUNNING_EMPTY_CODE = 0x0f
    RUN_CONTRACT = 0x10

    # call results are handled by call-post/err/revert processing in the interpreter loop


def call_work_proc(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()

    mode = CallMode(last.call_work.mode)

    if mode == CallMode.START:
        # return-to-step, so we can revert changes to contract etc. if call completes
        # A successful call will restore this step while preserving the state-root, returning remaining gas, etc.
        next.return_to_step = last.copy()
        next.call_work.mode = CallMode.LOAD_SCOPE
        return next
    if mode == CallMode.LOAD_SCOPE:
        next.contract.caller = last.call_work.caller
        next.contract.code_addr = last.call_work.code_addr
        next.contract.read_only = last.call_work.read_only
        next.contract.gas = last.call_work.gas
        next.contract.self_addr = last.call_work.addr
        next.contract.value = last.call_work.value

        next.call_work.mode = CallMode.RESET_INPUT
        return next
    if mode == CallMode.RESET_INPUT:
        next.contract.input = Input()
        next.call_work.mode = CallMode.LOAD_INPUT
        return next
    if mode == CallMode.LOAD_INPUT:
        in_size = next.contract.stack.back_u256(4)
        if in_size > 0:
            in_offset = last.call_work.input_offset

            # optimization: if not aligned with 32-bytes, make it align
            delta = 32 - (in_offset % 32)
            # we may already be nearly done, length within 32 bytes
            if delta > in_size:
                delta = in_size

            # at most 32 bytes, aligned with the 32-byte memory leaves
            input_data = last.contract.memory[in_offset:in_offset+delta]
            # append to existing input (touches 2 packed leaf nodes at most, and the length mixin)
            next.contract.input += input_data

            # next step will have adjusted params, to continue the copy process
            next.call_work.input_size = in_size - delta
            next.call_work.input_offset = in_offset + delta
            return next
        else:
            next.call_work.mode = CallMode.CALL_DEPTH_CHECK
            return next
    if mode == CallMode.CALL_DEPTH_CHECK:
        if last.contract.call_depth > CALL_CREATE_DEPTH:
            # TODO: unwind 1 up first, outside of call frame, then error from unwinded.
            next.exec_mode = ExecMode.ErrDepth
            return next
        else:
            next.call_work.mode = CallMode.READ_BALANCE
            return next
    if mode == CallMode.READ_BALANCE:
        # TODO
        next.call_work.mode = CallMode.CHECK_TRANSFER_VALUE
        return next
    if mode == CallMode.CHECK_TRANSFER_VALUE:
        value = next.call_work.value
        if value > 0:
            # TODO: read earlier retrieved balance
            amount = 123
            if amount < value:
                next.exec_mode = ExecMode.ErrInsufficientBalance
                return next

        next.call_work.mode = CallMode.CHECK_ACCOUNT_EXISTS
        return next
    if mode == CallMode.CHECK_ACCOUNT_EXISTS:
        # TODO
        next.call_work.mode = CallMode.CHECK_IF_PRECOMPILE
        return next
    if mode == CallMode.CHECK_IF_PRECOMPILE:
        # TODO
        next.call_work.mode = CallMode.CHECK_IF_PRECOMPILE
        return next
    if mode == CallMode.CREATE_TO_ACCOUNT:
        # TODO
        next.call_work.mode = CallMode.CREATE_TO_ACCOUNT
        return next
    if mode == CallMode.TRANSFER_VALUE:
        # TODO
        next.call_work.mode = CallMode.LOAD_CODE
        return next
    if mode == CallMode.LOAD_CODE:
        # TODO
        next.call_work.mode = CallMode.LOAD_PRECOMPILE
        return next
    if mode == CallMode.LOAD_PRECOMPILE:
        # TODO
        raise NotImplementedError
    if mode == CallMode.LOAD_REGULAR_CONTRACT_CODE_HASH:
        # TODO
        next.call_work.mode = CallMode.LOAD_REGULAR_CONTRACT_CODE
        return next
    if mode == CallMode.LOAD_REGULAR_CONTRACT_CODE:
        next.call_work.mode = CallMode.CHECK_RUNNING_EMPTY_CODE
        return next
    if mode == CallMode.CHECK_RUNNING_EMPTY_CODE:
        # TODO
        next.call_work.mode = CallMode.RUN_CONTRACT
        return next
    if mode == CallMode.RUN_CONTRACT:
        # TODO
        return next

    raise NotImplementedError
