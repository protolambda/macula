from .trace import StepsTrace, Processor
from .step import *
from .exec_mode import *
from typing import Protocol
from enum import Enum


class StateWork(Enum):
    CREATE_EXTERNALLY_OWNED_ACCOUNT = 0x00
    CREATE_CONTRACT_ACCOUNT = 0x01

    SUB_BALANCE = 0x10
    ADD_BALANCE = 0x11

    READ_CONTRAC_CODE = 0x20

    REMOVE_CONTRACT_CODE = 0x30

    READ_NONCE = 0x40
    SET_NONCE = 0x41

    # TODO: more state ops

    DONE = 0xff


def state_work_proc(self, trac: StepsTrace) -> Step:
    last = trac.last()
    db_op = StateDBOp(int(b32_to_uint256(last.sub_data[0])))
    if db_op == StateWork.CREATE_EXTERNALLY_OWNED_ACCOUNT:
        raise NotImplementedError  # TODO

    if db_op == StateWork.CREATE_CONTRACT_ACCOUNT:
        raise NotImplementedError  # TODO

    if db_op == StateWork.SUB_BALANCE:
        raise NotImplementedError  # TODO

    if db_op == StateWork.ADD_BALANCE:
        raise NotImplementedError  # TODO

    if db_op == StateWork.READ_CONTRAC_CODE:
        raise NotImplementedError  # TODO

    if db_op == StateWork.REMOVE_CONTRACT_CODE:
        raise NotImplementedError  # TODO

    if db_op == StateWork.READ_NONCE:
        raise NotImplementedError  # TODO

    if db_op == StateWork.SET_NONCE:
        raise NotImplementedError  # TODO

    raise NotImplementedError
