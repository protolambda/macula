from .params import STACK_LIMIT

def min_swap_stack(n: int) -> int:
    return min_stack(n, n)


def max_swap_stack(n: int) -> int:
    return max_stack(n, n)


def min_dup_stack(n: int) -> int:
    return min_stack(n, n+1)


def max_dup_stack(n: int) -> int:
    return max_stack(n, n+1)


def max_stack(pop: int, push: int) -> int:
    return STACK_LIMIT + pop - push


def min_stack(pops: int, push: int) -> int:
    return pops
