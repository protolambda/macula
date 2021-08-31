from .step import Stack, uint64, uint256


# calcMemSize64 calculates the required memory size, and returns
# the size and whether the result overflowed uint64
def calc_mem_size_64(off: uint256, l: uint256) -> (uint64, bool):
    if l >= 2**64:
        return uint64(0), True
    return calc_mem_size_64_with_uint(off, uint64(l))


def calc_mem_size_64_with_uint(off: uint256, l: uint64) -> (uint64, bool):
    if l == 0:
        return 0, False
    if off >= 2**64:  # check overflow
        return 0, True
    val = off + uint256(l)
    if val >= 2**64:
        return 0, True
    return uint64(val), False


def memory_sha3(stack: Stack) -> (uint64, bool):
    return calc_mem_size_64(stack.back_u256(0), stack.back_u256(1))


def memory_call_data_copy(stack: Stack) -> (uint64, bool):
    return calc_mem_size_64(stack.back_u256(0), stack.back_u256(2))


def memory_return_data_copy(stack: Stack) -> (uint64, bool):
    return calc_mem_size_64(stack.back_u256(0), stack.back_u256(2))


def memory_code_copy(stack: Stack) -> (uint64, bool):
    return calc_mem_size_64(stack.back_u256(0), stack.back_u256(2))


def memory_ext_code_copy(stack: Stack) -> (uint64, bool):
    return calc_mem_size_64(stack.back_u256(1), stack.back_u256(3))


def memory_mload(stack: Stack) -> (uint64, bool):
    return calc_mem_size_64_with_uint(stack.back_u256(0), uint64(32))


def memory_mstore8(stack: Stack) -> (uint64, bool):
    return calc_mem_size_64_with_uint(stack.back_u256(0), uint64(1))


def memory_mstore(stack: Stack) -> (uint64, bool):
    return calc_mem_size_64_with_uint(stack.back_u256(0), uint64(32))


def memory_create(stack: Stack) -> (uint64, bool):
    return calc_mem_size_64(stack.back_u256(1), stack.back_u256(2))


def memory_create2(stack: Stack) -> (uint64, bool):
    return calc_mem_size_64(stack.back_u256(1), stack.back_u256(2))


def memory_call(stack: Stack) -> (uint64, bool):
    # The return data size
    x, overflow = calc_mem_size_64(stack.back_u256(5), stack.back_u256(6))
    if overflow:
        return uint64(0), True
    # The input data size
    y, overflow = calc_mem_size_64(stack.back_u256(3), stack.back_u256(4))
    if overflow:
        return uint64(0), True
    if x > y:
        return x, False
    return y, False


def memory_delegate_call(stack: Stack) -> (uint64, bool):
    # The return data size
    x, overflow = calc_mem_size_64(stack.back_u256(4), stack.back_u256(5))
    if overflow:
        return uint64(0), True
    # The input data size
    y, overflow = calc_mem_size_64(stack.back_u256(2), stack.back_u256(3))
    if overflow:
        return uint64(0), True
    if x > y:
        return x, False
    return y, False


def memory_static_call(stack: Stack) -> (uint64, bool):
    # The return data size
    x, overflow = calc_mem_size_64(stack.back_u256(4), stack.back_u256(5))
    if overflow:
        return uint64(0), True
    # The input data size
    y, overflow = calc_mem_size_64(stack.back_u256(2), stack.back_u256(3))
    if overflow:
        return uint64(0), True
    if x > y:
        return x, False
    return y, False


def memory_return(stack: Stack) -> (uint64, bool):
    return calc_mem_size_64(stack.back_u256(0), stack.back_u256(1))


def memory_revert(stack: Stack) -> (uint64, bool):
    return calc_mem_size_64(stack.back_u256(0), stack.back_u256(1))


def memory_log(stack: Stack) -> (uint64, bool):
    return calc_mem_size_64(stack.back_u256(0), stack.back_u256(1))



