from .trace import StepsTrace, Processor
from .step import *
from .exec_mode import *

def progress(step: Step) -> step:
    # progress to the next opcode. Common between a lot of opcode steps
    step.pc += 1
    step.exec_mode = ExecMode.OpcodeLoad.value
    return step

def op_add(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    # leave 1 top stack slot in place,
    # more efficient to not change length more than necessary
    x, y = next.stack.pop_u256(), next.stack.peek_u256()
    next.stack.tweak_u256(x+y)
    return progress(next)

def op_sub(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    x, y = next.stack.pop_u256(), next.stack.peek_u256()
    next.stack.tweak_u256(x-y)
    return progress(next)

def op_div(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    x, y = next.stack.pop_u256(), next.stack.peek_u256()
    next.stack.tweak_u256(x // y)
    return progress(next)

# SDiv interprets x and y as two's complement signed integers,
# does a signed division on the two operands and sets z to the result.
# If y == 0, z is set to 0
def op_sdiv(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    x, y = next.stack.pop_u256(), next.stack.peek_u256()
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

    next.stack.tweak_u256(z)
    return progress(next)

def op_mul(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    x, y = next.stack.pop_u256(), next.stack.peek_u256()
    next.stack.tweak_u256(x*y)
    return progress(next)

# SMod interprets x and y as two's complement signed integers,
# sets z to (sign x) * { abs(x) modulus abs(y) }
# If y == 0, z is set to 0
def op_smod(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    x, y = next.stack.pop_u256(), next.stack.peek_u256()
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

    next.stack.tweak_u256(z)
    return progress(next)

def op_exp(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    x, y = next.stack.pop_u256(), next.stack.peek_u256()
    z = uint256((int(x)**int(y)) % ((1 << 256)-1))
    next.stack.tweak_u256(z)
    return progress(next)

def op_sign_extend(trac: StepsTrace) -> Step:
    raise NotImplementedError

def op_not(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    x = next.stack.peek_u256()
    x ^= (1 << 256)-1
    next.stack.tweak_u256(x)
    return progress(next)

def op_lt(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    x, y = next.stack.pop_u256(), next.stack.peek_u256()
    if x < y:
        y = 1
    else:
        y = 0
    next.stack.tweak_u256(y)
    return progress(next)

def op_gt(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    x, y = next.stack.pop_u256(), next.stack.peek_u256()
    if x > y:
        y = 1
    else:
        y = 0
    next.stack.tweak_u256(y)
    return progress(next)

def op_slt(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    x, y = next.stack.pop_u256(), next.stack.peek_u256()

    # signed ints now, not the SSZ uint256 anymore
    x, y = int(x), int(y)
    if x >= (1 << 255): x = x - (1 << 255)
    if y >= (1 << 255): y = y - (1 << 255)

    if x < y:
        y = 1
    else:
        y = 0
    next.stack.tweak_u256(y)
    return progress(next)

def op_sgt(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    x, y = next.stack.pop_u256(), next.stack.peek_u256()

    # signed ints now, not the SSZ uint256 anymore
    x, y = int(x), int(y)
    if x >= (1 << 255): x = x - (1 << 255)
    if y >= (1 << 255): y = y - (1 << 255)

    if x > y:
        y = 1
    else:
        y = 0
    next.stack.tweak_u256(y)
    return progress(next)

def op_eq(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    x, y = next.stack.pop_u256(), next.stack.peek_u256()
    if x == y:
        y = 1
    else:
        y = 0
    next.stack.tweak_u256(y)
    return progress(next)

def op_iszero(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    x = next.stack.peek_u256()
    if x == 0:
        x = 1
    else:
        x = 0
    next.stack.tweak_u256(x)
    return progress(next)

def op_and(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    x, y = next.stack.pop_u256(), next.stack.peek_u256()
    y = x & y
    next.stack.tweak_u256(y)
    return progress(next)

def op_or(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    x, y = next.stack.pop_u256(), next.stack.peek_u256()
    y = x | y
    next.stack.tweak_u256(y)
    return progress(next)

def op_xor(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    x, y = next.stack.pop_u256(), next.stack.peek_u256()
    y = x ^ y
    next.stack.tweak_u256(y)
    return progress(next)

def op_byte(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    th, val = next.stack.pop_u256(), next.stack.peek_b32()
    out = 0
    if th < 32:
        out = val[th]

    next.stack.tweak_u256(uint256(out))
    return progress(next)

def op_addmod(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    x, y, z = next.stack.pop_u256(), next.stack.pop_u256(), next.stack.peek_u256()
    if z != 0:
        z = uint256((int(x) + int(y)) % int(z))

    next.stack.tweak_u256(z)
    return progress(next)

def op_mulmod(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    x, y, z = next.stack.pop_u256(), next.stack.pop_u256(), next.stack.peek_u256()
    if z != 0:
        z = uint256((int(x) * int(y)) % int(z))

    next.stack.tweak_u256(z)
    return progress(next)


