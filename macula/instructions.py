from .trace import StepsTrace, Processor
from .step import *
from .exec_mode import *
from .state_work import *
from .call_work import *
from .params import *


def progress(step: Step) -> Step:
    # progress to the next opcode. Common between a lot of opcode steps
    step.contract.pc += 1
    step.exec_mode = ExecMode.OpcodeLoad
    return step


def op_add(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    # leave 1 top stack slot in place,
    # more efficient to not change length more than necessary
    x, y = next.contract.stack.pop_u256(), next.contract.stack.peek_u256()
    next.contract.stack.tweak_u256(x+y)
    return progress(next)


def op_sub(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    x, y = next.contract.stack.pop_u256(), next.contract.stack.peek_u256()
    next.contract.stack.tweak_u256(x-y)
    return progress(next)


def op_mul(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    x, y = next.contract.stack.pop_u256(), next.contract.stack.peek_u256()
    next.contract.stack.tweak_u256(x*y)
    return progress(next)


def op_div(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    x, y = next.contract.stack.pop_u256(), next.contract.stack.peek_u256()
    next.contract.stack.tweak_u256(x // y)
    return progress(next)


# SDiv interprets x and y as two's complement signed integers,
# does a signed division on the two operands and sets z to the result.
# If y == 0, z is set to 0
def op_sdiv(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    x, y = next.contract.stack.pop_u256(), next.contract.stack.peek_u256()
    z = 0
    if y != 0:
        # signed ints now, not the SSZ uint256 anymore
        x, y = int(x), int(y)
        if x >= (1 << 255): x = x - (1 << 255)
        if y >= (1 << 255): y = y - (1 << 255)
        z = x // y
        # back to uint256 representation
        if z < 0:
            z += 1 << 255
        z = uint256(z)

    next.contract.stack.tweak_u256(z)
    return progress(next)


def op_mod(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    x, y = next.contract.stack.pop_u256(), next.contract.stack.peek_u256()
    next.contract.stack.tweak_u256(x % y)
    return progress(next)


# SMod interprets x and y as two's complement signed integers,
# sets z to (sign x) * { abs(x) modulus abs(y) }
# If y == 0, z is set to 0
def op_smod(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    x, y = next.contract.stack.pop_u256(), next.contract.stack.peek_u256()
    z = 0
    if y != 0:
        # if negative, make it positive
        x_old = x
        if x >= (1 << 255): x = x - (1 << 255)
        if y >= (1 << 255): y = y - (1 << 255)
        z = x % y
        if x_old >= (1 << 255):
            if z >= (1 << 255): z = z - (1 << 255)
            else: z = z + (1 << 255)

    next.contract.stack.tweak_u256(z)
    return progress(next)


def op_exp(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    x, y = next.contract.stack.pop_u256(), next.contract.stack.peek_u256()
    z = uint256((int(x)**int(y)) % ((1 << 256)-1))
    next.contract.stack.tweak_u256(z)
    return progress(next)


def op_sign_extend(trac: StepsTrace) -> Step:
    raise NotImplementedError


def op_not(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    x = next.contract.stack.peek_u256()
    x ^= (1 << 256)-1
    next.contract.stack.tweak_u256(x)
    return progress(next)


def op_lt(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    x, y = next.contract.stack.pop_u256(), next.contract.stack.peek_u256()
    if x < y:
        y = 1
    else:
        y = 0
    next.contract.stack.tweak_u256(y)
    return progress(next)


def op_gt(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    x, y = next.contract.stack.pop_u256(), next.contract.stack.peek_u256()
    if x > y:
        y = 1
    else:
        y = 0
    next.contract.stack.tweak_u256(y)
    return progress(next)

def op_slt(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    x, y = next.contract.stack.pop_u256(), next.contract.stack.peek_u256()

    # signed ints now, not the SSZ uint256 anymore
    x, y = int(x), int(y)
    if x >= (1 << 255): x = x - (1 << 255)
    if y >= (1 << 255): y = y - (1 << 255)

    if x < y:
        y = 1
    else:
        y = 0
    next.contract.stack.tweak_u256(y)
    return progress(next)

def op_sgt(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    x, y = next.contract.stack.pop_u256(), next.contract.stack.peek_u256()

    # signed ints now, not the SSZ uint256 anymore
    x, y = int(x), int(y)
    if x >= (1 << 255): x = x - (1 << 255)
    if y >= (1 << 255): y = y - (1 << 255)

    if x > y:
        y = 1
    else:
        y = 0
    next.contract.stack.tweak_u256(y)
    return progress(next)

def op_eq(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    x, y = next.contract.stack.pop_u256(), next.contract.stack.peek_u256()
    if x == y:
        y = 1
    else:
        y = 0
    next.contract.stack.tweak_u256(y)
    return progress(next)

def op_iszero(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    x = next.contract.stack.peek_u256()
    if x == 0:
        x = 1
    else:
        x = 0
    next.contract.stack.tweak_u256(x)
    return progress(next)

def op_and(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    x, y = next.contract.stack.pop_u256(), next.contract.stack.peek_u256()
    y = x & y
    next.contract.stack.tweak_u256(y)
    return progress(next)

def op_or(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    x, y = next.contract.stack.pop_u256(), next.contract.stack.peek_u256()
    y = x | y
    next.contract.stack.tweak_u256(y)
    return progress(next)

def op_xor(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    x, y = next.contract.stack.pop_u256(), next.contract.stack.peek_u256()
    y = x ^ y
    next.contract.stack.tweak_u256(y)
    return progress(next)

def op_byte(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    th, val = next.contract.stack.pop_u256(), next.contract.stack.peek_b32()
    out = 0
    if th < 32:
        out = val[th]

    next.contract.stack.tweak_u256(uint256(out))
    return progress(next)

def op_addmod(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    x, y, z = next.contract.stack.pop_u256(), next.contract.stack.pop_u256(), next.contract.stack.peek_u256()
    if z != 0:
        z = uint256((int(x) + int(y)) % int(z))

    next.contract.stack.tweak_u256(z)
    return progress(next)

def op_mulmod(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    x, y, z = next.contract.stack.pop_u256(), next.contract.stack.pop_u256(), next.contract.stack.peek_u256()
    if z != 0:
        z = uint256((int(x) * int(y)) % int(z))

    next.contract.stack.tweak_u256(z)
    return progress(next)


def op_shl(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    shift, value = next.contract.stack.pop_u256(), next.contract.stack.peek_u256()
    if shift < 256:
        value = value << shift
    else:
        value = 0

    next.contract.stack.tweak_u256(value)
    return progress(next)


def op_shr(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    shift, value = next.contract.stack.pop_u256(), next.contract.stack.peek_u256()
    if shift < 256:
        value = value >> shift
    else:
        value = 0

    next.contract.stack.tweak_u256(value)
    return progress(next)


def op_sar(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    shift, value = next.contract.stack.pop_u256(), next.contract.stack.peek_u256()
    if shift > 256:
        # 0 or negative -> clear the value
        if value == 0 or value >= (1 << 255):
            value = uint256(0)
        else:
            # max negative shift: all bits set
            value = uint256((1 << 256)-1)
    else:
        # If the MSB is 0, SRsh is same as Rsh.
        if value >= (1 << 255):
            value = value >> shift
        elif shift != 0:
            # TODO ugly Signed/Arithmetic right shift
            raise NotImplementedError

    next.contract.stack.tweak_u256(value)
    return progress(next)


def op_sha3(trac: StepsTrace) -> Step:
    # TODO sha3 steps
    raise NotImplementedError


def op_address(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    next.contract.stack.push_b32(last.contract.self_addr.to_b32())
    return progress(next)


def op_balance(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    # Do we have the balance yet?
    if last.state_work.mode == StateWorkMode.RETURNED:
        last.state_work.mode = StateWorkMode.IDLE  # kindly reset the mode, to not mess up future uses.
        value: StateWork_GetBalance = last.state_work.work.value()
        # Overwrite the address argument with the result
        next.contract.stack.tweak_u256(uint256(value.balance_result))
        return progress(next)
    else:
        assert last.state_work.mode == StateWorkMode.IDLE
        addr = Address.from_b32(last.contract.stack.peek_b32())
        next.state_work.mode = StateWorkMode.REQUESTING
        next.state_work.mode_on_finish = StateWorkMode.RETURNED
        next.state_work.work.change(
            selector=StateWorkType.GET_BALANCE,
            value=StateWork_GetBalance(address=addr)
        )
        next.return_to_step.change(selector=1, value=last)
        next.exec_mode = ExecMode.StateWork
        return next


def op_origin(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    next.contract.stack.push_b32(last.contract.origin.to_b32())
    return progress(next)


def op_caller(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    next.contract.stack.push_b32(last.contract.caller.to_b32())
    return progress(next)


def op_call_value(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    next.contract.stack.push_uint256(last.contract.value)
    return progress(next)


def op_call_data_load(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    x = last.contract.stack.peek_u256()
    if x < (1 << 64):
        next.contract.stack.tweak_b32(last.contract.input.get_data_b32(uint64(x)))
    else:
        next.contract.stack.tweak_b32(Bytes32())

    return progress(next)


def op_call_data_size(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    next.contract.stack.push_u256(uint256(len(last.contract.input)))
    return progress(next)


def op_call_data_copy(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    # we split this up in steps, until the copy is done

    mem_offset = last.contract.stack.back_u256(0)
    data_offset = last.contract.stack.back_u256(1)
    length = last.contract.stack.back_u256(2)

    if data_offset >= 2**64:  # overflow check, stays well under uint256 this way
        data_offset = 2**64 - 1

    # optimization: if not aligned with 32-bytes, make it align
    delta = 32 - (data_offset % 32)
    # we may already be nearly done, length within 32 bytes
    if delta > length:
        delta = length

    if length > 0:
        # Different than other copy funcs:
        # copying from input data beyond actual range is allowed, it just results in zeroes.
        # Complete the (maybe not aligned) last bit of actual input,
        # then start on the padding work in next steps (if any)
        if data_offset < len(last.contract.input) < data_offset+delta:
            delta = len(last.contract.input) - data_offset

        if data_offset >= len(last.contract.input):
            data_copy = b"\x00" * delta
        else:
            data_copy = bytes(last.contract.input[data_offset:data_offset+delta])

        # touches two words of memory if the memory offset is not aligned, but that's still manageable
        next.contract.memory[mem_offset:mem_offset+delta] = data_copy
        mem_offset += delta
        data_offset += delta
        length -= delta

    # complete or continue with remaining copy work
    if length == 0:
        # copy finished, we can progress to the next opcode, after popping the stack vars
        next.contract.stack.pop()
        next.contract.stack.pop()
        next.contract.stack.pop()
        return progress(next)
    else:
        # we'll just use the existing stack vars to track progress. We get rid of them at the end.
        next.contract.stack.tweak_back_u256(mem_offset, 0)
        next.contract.stack.tweak_back_u256(data_offset, 1)
        next.contract.stack.tweak_back_u256(length, 2)
        # don't go to the next opcode yet, but instead repeat this opcode, now with the reduced work.
        # we keep doing this, until the copy work is done.
        return next


def op_return_data_size(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    next.contract.stack.push_u256(uint256(len(last.contract.ret_data)))
    return progress(next)


def op_return_data_copy(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    # we split this up in steps, until the copy is done

    mem_offset = last.contract.stack.back_u256(0)
    data_offset = last.contract.stack.back_u256(1)
    length = last.contract.stack.back_u256(2)

    if data_offset >= 2**64:  # overflow check, stays well under uint256 this way
        data_offset = 2**64 - 1

    # Different than other copy instructions:
    # check bounds of the copy (memory is checked by interpreter, return data is not)
    if data_offset >= 2**63 or length >= 2**63 or len(last.contract.ret_data) < data_offset+length:
        next.exec_mode = ExecMode.ErrReturnDataOutOfBounds
        return next

    # optimization: if not aligned with 32-bytes, make it align
    delta = 32 - (data_offset % 32)
    # we may already be nearly done, length within 32 bytes
    if delta > length:
        delta = length

    if length > 0:
        data_copy = bytes(last.contract.ret_data[data_offset:data_offset+delta])
        # touches two words of memory if the memory offset is not aligned, but that's still manageable
        next.contract.memory[mem_offset:mem_offset+delta] = data_copy
        mem_offset += delta
        data_offset += delta
        length -= delta

    # complete or continue with remaining copy work
    if length == 0:
        # copy finished, we can progress to the next opcode, after popping the stack vars
        next.contract.stack.pop()
        next.contract.stack.pop()
        next.contract.stack.pop()
        return progress(next)
    else:
        # we'll just use the existing stack vars to track progress. We get rid of them at the end.
        next.contract.stack.tweak_back_u256(mem_offset, 0)
        next.contract.stack.tweak_back_u256(data_offset, 1)
        next.contract.stack.tweak_back_u256(length, 2)
        # don't go to the next opcode yet, but instead repeat this opcode, now with the reduced work.
        # we keep doing this, until the copy work is done.
        return next



def op_ext_code_size(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    # Do we have the size yet?
    if last.state_work.mode == StateWorkMode.RETURNED:
        last.state_work.mode = StateWorkMode.IDLE  # kindly reset the mode, to not mess up future uses.
        value: StateWork_GetContractCodeSize = last.state_work.work.value()
        # Overwrite the address argument with the result
        next.contract.stack.tweak_u256(uint256(value.size))
        return progress(next)
    else:
        assert last.state_work.mode == StateWorkMode.IDLE
        addr = Address.from_b32(last.contract.stack.peek_b32())
        next.state_work.mode = StateWorkMode.REQUESTING
        next.state_work.mode_on_finish = StateWorkMode.RETURNED
        next.state_work.work.change(
            selector=StateWorkType.GET_CONTRACT_CODE_SIZE,
            value=StateWork_GetContractCodeSize(address=addr)
        )
        next.return_to_step.change(selector=1, value=last)
        next.exec_mode = ExecMode.StateWork
        return next


def op_code_size(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    next.contract.stack.push_u256(uint256(len(last.contract.code)))
    return progress(next)


def op_code_copy(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    # we split this up in steps, until the copy is done

    mem_offset = last.contract.stack.back_u256(0)
    code_offset = last.contract.stack.back_u256(1)
    length = last.contract.stack.back_u256(2)

    if code_offset >= 2**64:  # overflow check, stays well under uint256 this way
        code_offset = 2**64 - 1

    # optimization: if not aligned with 32-bytes, make it align
    delta = 32 - (code_offset % 32)
    # we may already be nearly done, length within 32 bytes
    if delta > length:
        delta = length

    if length > 0:
        code_copy = bytes(last.contract.code[code_offset:code_offset+delta])
        # touches two words of memory if the memory offset is not aligned, but that's still manageable
        next.contract.memory[mem_offset:mem_offset+delta] = code_copy
        mem_offset += delta
        code_offset += delta
        length -= delta

    # complete or continue with remaining copy work
    if length == 0:
        # copy finished, we can progress to the next opcode, after popping the stack vars
        next.contract.stack.pop()
        next.contract.stack.pop()
        next.contract.stack.pop()
        return progress(next)
    else:
        # we'll just use the existing stack vars to track progress. We get rid of them at the end.
        next.contract.stack.tweak_back_u256(mem_offset, 0)
        next.contract.stack.tweak_back_u256(code_offset, 1)
        next.contract.stack.tweak_back_u256(length, 2)
        # don't go to the next opcode yet, but instead repeat this opcode, now with the reduced work.
        # we keep doing this, until the copy work is done.
        return next


def op_ext_code_copy(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    # TODO
    raise NotImplementedError


def op_ext_code_hash(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    # Do we have the code hash yet?
    if last.state_work.mode == StateWorkMode.RETURNED:
        last.state_work.mode = StateWorkMode.IDLE  # kindly reset the mode, to not mess up future uses.
        value: StateWork_GetContractCodeHash = last.state_work.work.value()
        # Overwrite the address argument with the result
        next.contract.stack.tweak_b32(value.code_hash_result)
        return progress(next)
    else:
        assert last.state_work.mode == StateWorkMode.IDLE
        addr = Address.from_b32(last.contract.stack.peek_b32())
        next.state_work.mode = StateWorkMode.REQUESTING
        next.state_work.mode_on_finish = StateWorkMode.RETURNED
        next.state_work.work.change(
            selector=StateWorkType.GET_CONTRACT_CODE_HASH,
            value=StateWork_GetContractCodeHash(address=addr)
        )
        next.return_to_step.change(selector=1, value=last)
        next.exec_mode = ExecMode.StateWork
        return next


def op_gas_price(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    next.contract.stack.push_u256(last.contract.gas_price)
    return progress(next)


def op_block_hash(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    num = last.contract.stack.peek_u256()
    # upper bound (excl.) current block number
    upper = last.block.block_number
    # lower bound (incl.): ensure 256 history, or clip to 0 genesis
    if upper < 257:
        lower = 0
    else:
        lower = upper - 256
    if num >= lower and num < upper:
        next.contract.stack.tweak_b32(last.history.block_hashes[num % 256])
    else:
        next.contract.stack.tweak_b32(Bytes32())
    raise NotImplementedError


def op_coinbase(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    next.contract.stack.push_b32(last.block.coinbase.to_b32())
    return progress(next)


def op_timestamp(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    next.contract.stack.push_u256(uint256(last.block.time))
    return progress(next)


def op_number(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    next.contract.stack.push_u256(uint256(last.block.block_number))
    return progress(next)


def op_difficulty(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    next.contract.stack.push_u256(last.block.difficulty)
    return progress(next)


def op_gas_limit(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    next.contract.stack.push_u256(uint256(last.block.gas_limit))
    return progress(next)


def op_pop(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    next.contract.stack.pop_b32()
    return progress(next)

def op_mload(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    offset = uint64(last.contract.stack.peek_u256())
    next.contract.stack.tweak_u256(last.contract.memory.get_ptr_32_bytes(offset))
    return progress(next)

def op_mstore(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    m_start, val = next.contract.stack.pop_u256(), next.contract.stack.pop_b32()
    next.contract.memory.set_32_bytes(m_start, val)
    return progress(next)


def op_mstore8(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    off, val = next.contract.stack.pop_u256(), next.contract.stack.pop_u256()
    # safe, memory-size and gas funcs check this already
    next.contract.memory[off] = uint8(val & 0xff)
    return progress(next)


def op_sload(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    # Do we have the storage value yet?
    if last.state_work.mode == StateWorkMode.RETURNED:
        last.state_work.mode = StateWorkMode.IDLE  # kindly reset the mode, to not mess up future uses.
        value: StateWork_StorageRead = last.state_work.work.value()
        # Overwrite the address argument with the result
        next.contract.stack.tweak_b32(value.value_result)
        return progress(next)
    else:
        assert last.state_work.mode == StateWorkMode.IDLE
        storage_hash = last.contract.stack.peek_b32()
        next.state_work.mode = StateWorkMode.REQUESTING
        next.state_work.mode_on_finish = StateWorkMode.RETURNED
        next.state_work.work.change(
            selector=StateWorkType.STORAGE_READ,
            value=StateWork_StorageRead(address=last.contract.addr, key=storage_hash)
        )
        next.return_to_step.change(selector=1, value=last)
        next.exec_mode = ExecMode.StateWork
        return next


def op_sstore(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    # Have we written the storage value yet?
    if last.state_work.mode == StateWorkMode.RETURNED:
        last.state_work.mode = StateWorkMode.IDLE  # kindly reset the mode, to not mess up future uses.
        # The state-root was updated by the state-work, we can progress to next instruction now
        return progress(next)
    else:
        assert last.state_work.mode == StateWorkMode.IDLE
        storage_pos = last.contract.stack.back_b32(0)
        storage_val = last.contract.stack.back_b32(1)

        next.state_work.mode = StateWorkMode.REQUESTING
        next.state_work.mode_on_finish = StateWorkMode.RETURNED
        next.state_work.work.change(
            selector=StateWorkType.STORAGE_WRITE,
            value=StateWork_StorageWrite(
                address=last.contract.addr,
                key=storage_pos,
                value=storage_val,
            )
        )
        next.return_to_step.change(selector=1, value=last)
        next.exec_mode = ExecMode.StateWork
        return next


def op_jump(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    pos = next.contract.stack.pop_u256()
    if not last.contract.code.valid_jump_dest(pos):
        next.exec_mode = ExecMode.ErrInvalidJump
        return next
    next.contract.pc = uint64(pos)
    return progress(next)


def op_jump_i(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    pos, cond = next.contract.stack.pop_u256(), next.contract.stack.pop_u256()
    if cond != uint256(0):
        if not last.contract.code.valid_jump_dest(pos):
            next.exec_mode = ExecMode.ErrInvalidJump
            return next
        # perform jump
        next.contract.pc = pos
        next.exec_mode = ExecMode.OpcodeLoad
        return next
    else:
        # just go to next opcode, jump conditional was false
        return progress(next)


def op_jump_dest(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    # no-op, except for moving onto the next opcode
    return progress(next)


def op_pc(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    next.contract.stack.push_u256(uint256(last.contract.pc))
    return progress(next)


def op_msize(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    next.contract.stack.push_u256(uint256(len(last.contract.memory)))
    return progress(next)


def op_gas(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    next.contract.stack.push_u256(uint256(last.contract.gas))
    return progress(next)


def op_create(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    # TODO
    raise NotImplementedError


def op_create2(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    # TODO
    raise NotImplementedError


def op_call(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()

    # TODO: geth uses interpreter.evm.callGasTemp here instead, modifying it during gas computation
    gas = last.contract.stack.back_u256(0)
    addr = Address.from_b32(last.contract.stack.back_b32(1))
    value = last.contract.stack.back_u256(2)
    input_offset = last.contract.stack.back_u256(3)
    input_size = last.contract.stack.back_u256(4)
    return_offset = last.contract.stack.back_u256(5)
    return_size = last.contract.stack.back_u256(6)

    # pop it all at once
    next.contract.stack.remove(7)

    if value != uint256(0):
        gas += CALL_STIPEND

    caller = last.contract.addr

    # completely reset the call work scope
    # (sub-tree, just a single node to merge into next state effectively)
    next.call_work = CallWorkScope(
        mode=CallMode.START,
        caller=caller,
        code_addr=addr,
        read_only=last.contract.read_only,  # inherit readonly mode
        gas=gas,
        addr=addr,
        value=value,
        input_offset=input_offset,
        input_size=input_size,
        return_offset=return_offset,
        return_size=return_size,
    )
    next.exec_mode = ExecMode.CallSetup

    # stack result push, return data memory copy and gas return is all part of call work
    return next


def op_call_code(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()

    # TODO: geth uses interpreter.evm.callGasTemp here instead, modifying it during gas computation
    gas = last.contract.stack.back_u256(0)
    addr = Address.from_b32(last.contract.stack.back_b32(1))
    value = last.contract.stack.back_u256(2)
    input_offset = last.contract.stack.back_u256(3)
    input_size = last.contract.stack.back_u256(4)
    return_offset = last.contract.stack.back_u256(5)
    return_size = last.contract.stack.back_u256(6)

    # pop it all at once
    next.contract.stack.remove(7)

    if value != uint256(0):
        gas += CALL_STIPEND

    caller = last.contract.addr

    # completely reset the call work scope
    # (sub-tree, just a single node to merge into next state effectively)
    next.call_work = CallWorkScope(
        mode=CallMode.START,
        caller=caller,
        code_addr=addr,
        read_only=last.contract.read_only,  # inherit readonly mode
        gas=gas,
        addr=caller,  # CODE-CALL calls code, without changing address
        value=value,
        input_offset=input_offset,
        input_size=input_size,
        return_offset=return_offset,
        return_size=return_size,
    )
    next.exec_mode = ExecMode.CallSetup

    # stack result push, return data memory copy and gas return is all part of call work
    return next


def op_delegate_call(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()

    # TODO: geth uses interpreter.evm.callGasTemp here instead, modifying it during gas computation
    gas = last.contract.stack.back_u256(0)
    addr = Address.from_b32(last.contract.stack.back_b32(1))
    # no value argument, as it's delegated instead
    input_offset = last.contract.stack.back_u256(2)
    input_size = last.contract.stack.back_u256(3)
    return_offset = last.contract.stack.back_u256(4)
    return_size = last.contract.stack.back_u256(5)

    # pop it all at once
    next.contract.stack.remove(6)

    # delegate the caller and value
    caller = last.contract.caller
    value = last.contract.value

    # completely reset the call work scope
    # (sub-tree, just a single node to merge into next state effectively)
    next.call_work = CallWorkScope(
        mode=CallMode.START,
        caller=caller,
        code_addr=addr,
        read_only=last.contract.read_only,  # inherit readonly mode
        gas=gas,
        addr=last.contract.addr,  # like CODE-CALL, the new self-address is the current address
        value=value,
        input_offset=input_offset,
        input_size=input_size,
        return_offset=return_offset,
        return_size=return_size,
    )
    next.exec_mode = ExecMode.CallSetup

    # stack result push, return data memory copy and gas return is all part of call work
    return next


def op_static_call(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()

    # TODO: geth uses interpreter.evm.callGasTemp here instead, modifying it during gas computation
    gas = last.contract.stack.back_u256(0)
    addr = Address.from_b32(last.contract.stack.back_b32(1))
    # no value argument, as it would affect state, and this call will be read-only
    input_offset = last.contract.stack.back_u256(2)
    input_size = last.contract.stack.back_u256(3)
    return_offset = last.contract.stack.back_u256(4)
    return_size = last.contract.stack.back_u256(5)

    # pop it all at once
    next.contract.stack.remove(6)

    caller = last.contract.addr

    # completely reset the call work scope
    # (sub-tree, just a single node to merge into next state effectively)
    next.call_work = CallWorkScope(
        mode=CallMode.START,
        caller=caller,
        code_addr=addr,
        read_only=True,  # enter read-only mode
        gas=gas,
        addr=addr,
        value=0,  # no value transfer
        input_offset=input_offset,
        input_size=input_size,
        return_offset=return_offset,
        return_size=return_size,
    )
    next.exec_mode = ExecMode.CallSetup

    # stack result push, return data memory copy and gas return is all part of call work
    return next


def op_return(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()

    size = last.contract.stack.back_u256(1)
    if size > 0:
        # TODO: copying one byte at a time because it is simple, but could try batch in <= 32 at a time
        offset = last.contract.stack.back_u256(0)
        byte_value = last.contract.memory[offset]  # interpreter already did gas check and memory expansion
        next.contract.ret_data.append(byte_value)
        next.contract.stack.tweak_back_u256(size-1, 1)
        next.contract.stack.tweak_back_u256(offset+1, 0)
        return next
    else:
        next.contract.stack.pop()
        next.contract.stack.pop()
        next.exec_mode = ExecMode.CallPost
        return next


def op_revert(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()

    size = last.contract.stack.back_u256(1)
    if size > 0:
        # TODO: copying one byte at a time because it is simple, but could try batch in <= 32 at a time
        offset = last.contract.stack.back_u256(0)
        byte_value = last.contract.memory[offset]  # interpreter already did gas check and memory expansion
        next.contract.ret_data.append(byte_value)
        next.contract.stack.tweak_back_u256(size-1, 1)
        next.contract.stack.tweak_back_u256(offset+1, 0)
        return next
    else:
        next.contract.stack.pop()
        next.contract.stack.pop()
        next.exec_mode = ExecMode.CallRevert
        return next


def op_stop(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    # halting opcode
    next.exec_mode = ExecMode.ErrSTOP
    return next


def op_self_destruct(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    # Do we have self-destructed yet?
    if last.state_work.mode == StateWorkMode.RETURNED:
        last.state_work.mode = StateWorkMode.IDLE  # kindly reset the mode, to not mess up future uses.
        # value: StateWork_SelfDestruct = last.state_work.work.value()
        # pop the beneficiary address from the stack
        next.contract.stack.pop()
        return progress(next)
    else:
        assert last.state_work.mode == StateWorkMode.IDLE
        beneficiary = Address.from_b32(last.contract.stack.peek_b32())
        next.state_work.mode = StateWorkMode.REQUESTING
        next.state_work.mode_on_finish = StateWorkMode.RETURNED
        next.state_work.work.change(
            selector=StateWorkType.SELF_DESTRUCT_ACCOUNT,
            value=StateWork_SelfDestruct(
                destruct_address=last.contract.self_addr,
                beneficiary_address=beneficiary
            )
        )
        next.return_to_step.change(selector=1, value=last)
        next.exec_mode = ExecMode.StateWork
        return next


def make_log(size: int) -> Processor:
    def op_log(trac: StepsTrace) -> Step:
        last = trac.last()
        next = last.copy()
        m_start, m_size = next.contract.stack.pop_u256(), next.contract.stack.pop_u256()
        topics = []
        for i in range(size):
            top = next.contract.stack.pop_b32()
            topics.append(top)

        # TODO: copy data into log in small pieces? How large can log data be?
        data = list(last.contract.memory[m_start:m_start+m_size])

        next.tx.logs.append(Log(
            address=last.contract.self_addr,
            topics=topics,
            data=data,
        ))

        return progress(next)
    return op_log


def op_push1(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    code_len = len(last.contract.code)
    pc = last.contract.pc + 1  # read after current opcode
    if pc < code_len:
        val: uint8 = last.contract.code[pc]
        next.contract.stack.push_u256(uint256(val))
    else:
        next.contract.stack.push_u256(uint256(0))
    pc += 1  # continue after pushed byte (will be 0 STOP opcode if already beyond code length)
    next.contract.pc = pc
    next.exec_mode = ExecMode.OpcodeLoad
    return next


def make_push(size: int, push_byte_size: int) -> Processor:
    assert push_byte_size <= 32
    def op_push(trac: StepsTrace) -> Step:
        last = trac.last()
        next = last.copy()
        # don't read any code out of bounds
        code_len = len(last.contract.code)
        start_min = code_len
        pc = last.contract.pc
        if pc + 1 < start_min:
            start_min = pc + 1
        end_min = code_len
        if start_min + push_byte_size < end_min:
            end_min = start_min + push_byte_size
        # push_byte_size <= 32, get the code (it may not align with 32 byte tree leafs though)
        content = last.contract.code[start_min:end_min]
        if end_min - start_min < 32:
            # right pad to 32 bytes
            content += b"\x00" * (32 - (end_min - start_min))
        next.contract.stack.push_b32(Bytes32(content))
        next.contract.pc = pc + size
        next.exec_mode = ExecMode.OpcodeLoad
        return next
    return op_push


def make_dup(size: uint8) -> Processor:
    def op_dup(trac: StepsTrace) -> Step:
        last = trac.last()
        next = last.copy()
        next.contract.stack.dup(size)
        raise progress(next)
    return op_dup


def make_swap(size: uint8) -> Processor:
    # switch n + 1 otherwise n would be swapped with n
    size += 1

    def op_swap(trac: StepsTrace) -> Step:
        last = trac.last()
        next = last.copy()
        next.contract.stack.swap(size)
        raise progress(next)
    return op_swap


