from .trace import StepsTrace, Processor
from .step import *
from .exec_mode import *
from typing import Protocol
from enum import Enum


class StateDBOp(Enum):
    CreateAccount = 0
    SubBalance = 0
    # TODO


class StateDB(Protocol):

    def proc_state_db_step(self, trac: StepsTrace) -> Step:
        last = trac.last()
        db_op = StateDBOp(int(b32_to_uint256(last.sub_data[0])))
        if db_op == StateDBOp.CreateAccount:
            return self.handle_create_account(trac)
        if db_op == StateDBOp.SubBalance:
            return self.handle_sub_balance(trac)
        # TODO more steps

    # TODO: split up every helper into a "setup" phase to commit to the data,
    #   and a "handle" phase to process the state work.
    def setup_create_account(self, trac: StepsTrace, address: Address) -> Step:
        last = trac.last()
        next = last.copy()
        next.sub_data[0] = 0x01  # create account
        next.sub_data[1] = address.to_b32()
        next.exec_mode = ExecMode.StateDB.value
        next.return_to_step = last.hash_tree_root()
        return next

    def handle_create_account(self, trac: StepsTrace) -> Step:
        ...

    def sub_balance(self, address: Address, v: uint256) -> None:
        ...
        # 1. get previous balance
        #    1.1. account proof
        #       1.1.1. MPT read proof
        #    1.2. store proven account
        # 2. add balance values
        # 3. store balance
        #    1.1. state-root updating proof
        #       1.1.1. MPT write proof
        #       1.1.2. update state-root

    def add_balance(self, address: Address, v: uint256) -> None:
        ...

    def get_balance(self, address: Address) -> uint256:
        ...

    def get_nonce(self, address: Address) -> uint64:
        ...

    def set_nonce(self, address: Address, nonce: uint64):
        ...

    def get_code_size(self, address: Address) -> uint64:
        ...

    # TODO: and more helpers to handle state
