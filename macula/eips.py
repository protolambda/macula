from .instructions import progress
from .trace import StepsTrace
from .step import Step, uint256, StateWorkMode, StateWork_GetBalance, StateWorkType
from .params import CHAIN_ID
from .exec_mode import ExecMode


def op_chain_id(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    next.contract.stack.push_b32(CHAIN_ID)
    return progress(next)


def op_base_fee(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    next.contract.stack.push_u256(last.block.base_fee)
    return progress(next)


def op_self_balance(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    # Do we have the balance yet?
    if last.state_work.mode == StateWorkMode.RETURNED:
        last.state_work.mode = StateWorkMode.IDLE  # kindly reset the mode, to not mess up future uses.
        value: StateWork_GetBalance = last.state_work.work.value()
        next.contract.stack.push_u256(uint256(value.balance_result))
        return progress(next)
    else:
        assert last.state_work.mode == StateWorkMode.IDLE
        next.state_work.mode = StateWorkMode.REQUESTING
        next.state_work.mode_on_finish = StateWorkMode.RETURNED
        next.state_work.work.change(
            selector=StateWorkType.GET_BALANCE,
            value=StateWork_GetBalance(address=last.contract.self_addr)
        )
        next.return_to_step.change(selector=1, value=last)
        next.exec_mode = ExecMode.StateWork
        return next
