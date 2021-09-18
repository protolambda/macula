from .trace import StepsTrace, Processor
from .step import Step
from .exec_mode import ExecMode

def memory_gas_cost():
    # TODO
    ...


def dyn_gas_done(next: Step) -> Step:
    # Continue to the next interpreter step: the memory-size update
    next.exec_mode = ExecMode.UpdateMemorySize
    return next


def gas_call_data_copy(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    # TODO
    return dyn_gas_done(next)


def gas_code_copy(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    # TODO
    return dyn_gas_done(next)


def gas_ext_code_copy(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    # TODO
    return dyn_gas_done(next)


def gas_ext_code_copy(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    # TODO
    return dyn_gas_done(next)


def gas_return_data_copy(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    # TODO
    return dyn_gas_done(next)


def gas_sstore(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    # TODO
    return dyn_gas_done(next)


def gas_sstore_eip2200(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    # TODO
    return dyn_gas_done(next)


def make_gas_log(n: int) -> Processor:
    def gas_log(trac: StepsTrace) -> Step:
        last = trac.last()
        next = last.copy()
        # TODO
        return dyn_gas_done(next)
    return gas_log


def gas_sha3(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    # TODO
    return dyn_gas_done(next)


def gas_pure_memory_gas_cost(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    # TODO
    return dyn_gas_done(next)


gas_return = gas_pure_memory_gas_cost
gas_revert = gas_pure_memory_gas_cost
gas_mload = gas_pure_memory_gas_cost
gas_mstore8 = gas_pure_memory_gas_cost
gas_mstore = gas_pure_memory_gas_cost
gas_create = gas_pure_memory_gas_cost


def gas_create2(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    # TODO
    return dyn_gas_done(next)


def gas_exp_frontier(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    # TODO
    return dyn_gas_done(next)


def gas_exp_eip158(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    # TODO
    return dyn_gas_done(next)


def gas_call(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    # TODO
    return dyn_gas_done(next)


def gas_call_code(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    # TODO
    return dyn_gas_done(next)


def gas_delegate_call(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    # TODO
    return dyn_gas_done(next)


def gas_static_call(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    # TODO
    return dyn_gas_done(next)


def gas_self_destruct(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    # TODO
    return dyn_gas_done(next)


