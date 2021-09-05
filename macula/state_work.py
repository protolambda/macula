from .trace import StepsTrace, Processor
from .step import *
from .exec_mode import *
from typing import Protocol
from enum import Enum


def state_work_proc(self, trac: StepsTrace) -> Step:
    last = trac.last()
    state_mode = StateWorkMode(int(last.state_work_scope.state_work.selector()))

    # TODO: implement state actions
    if state_mode == StateWorkMode.NO_ACTION:
        value: None = last.state_work_scope.state_work.value()
    if state_mode == StateWorkMode.HAS_ACCOUNT:
        value: StateWork_HasAccount = last.state_work_scope.state_work.value()
    if state_mode == StateWorkMode.CREATE_ACCOUNT:
        value: StateWork_CreateAccount = last.state_work_scope.state_work.value()
    if state_mode == StateWorkMode.SUB_BALANCE:
        value: StateWork_SubBalance = last.state_work_scope.state_work.value()
    if state_mode == StateWorkMode.ADD_BALANCE:
        value: StateWork_AddBalance = last.state_work_scope.state_work.value()
    if state_mode == StateWorkMode.READ_CONTRACT_CODE_HASH:
        value: StateWork_ReadContractCodeHash = last.state_work_scope.state_work.value()
    if state_mode == StateWorkMode.READ_CONTRACT_CODE:
        value: StateWork_ReadContractCode = last.state_work_scope.state_work.value()
    if state_mode == StateWorkMode.REMOVE_CONTRACT_CODE:
        value: StateWork_RemoveContractCode = last.state_work_scope.state_work.value()
    if state_mode == StateWorkMode.READ_NONCE:
        value: StateWork_ReadNonce = last.state_work_scope.state_work.value()
    if state_mode == StateWorkMode.SET_NONCE:
        value: StateWork_SetNonce = last.state_work_scope.state_work.value()
    if state_mode == StateWorkMode.STORAGE_READ:
        value: StateWork_StorageRead = last.state_work_scope.state_work.value()
    if state_mode == StateWorkMode.STORAGE_WRITE:
        value: StateWork_StorageWrite = last.state_work_scope.state_work.value()

    raise NotImplementedError
