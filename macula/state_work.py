from .trace import StepsTrace, Processor
from .step import *
from .exec_mode import *
from .mpt_work import *
import rlp


# User instructions:
#  Enter state-work:
#    - in mode REQUESTING
#    - with a work-type (which contains request params)
#    - a return_to_step
#    - mode_on_finish set to RETURNED
#  Once done, it will continue with the return_to_step, with the state-work updated, and in mode RETURNED.
#  As receiver of the return, reset the mode to IDLE.
def state_work_proc(trac: StepsTrace) -> Step:
    last = trac.last()
    mode = StateWorkMode(int(last.state_work.mode))
    if mode == StateWorkMode.IDLE:
        raise Exception("state-work should never be in idle state during processing")
    if mode == StateWorkMode.RETURNED:
        raise Exception("state-work should never be in returned state during processing")

    if mode == StateWorkMode.REQUESTING:
        typ = StateWorkType(int(last.state_work.work.selector()))
        # TODO: implement state actions
        if typ == StateWorkType.NO_ACTION:
            value: None = last.state_work.work.value()
            raise NotImplementedError
        if typ == StateWorkType.HAS_ACCOUNT:
            value: StateWork_HasAccount = last.state_work.work.value()
            raise NotImplementedError
        if typ == StateWorkType.CREATE_ACCOUNT:
            value: StateWork_CreateAccount = last.state_work.work.value()
            raise NotImplementedError
        if typ == StateWorkType.SUB_BALANCE:
            value: StateWork_SubBalance = last.state_work.work.value()
            raise NotImplementedError
        if typ == StateWorkType.ADD_BALANCE:
            value: StateWork_AddBalance = last.state_work.work.value()
            raise NotImplementedError
        if typ == StateWorkType.READ_CONTRACT_CODE_HASH:
            if last.mpt_work.mode == MPTAccessMode.DONE.value:
                code_hash: Bytes32
                if last.mpt_work.fail_lookup != 0:
                    code_hash = Bytes32()  # If we failed to find the account, it will be a 0 hash
                else:
                    account_data = rlp.decode(last.mpt_work.value)
                    code_hash = account_data[3]  # 4th field is the code hash

                caller = last.return_to_step.value()
                next: Step = caller.copy()
                next.state_work.mode = last.state_work.mode_on_finish
                value: StateWork_ReadContractCodeHash = next.state_work.work.value()
                value.code_hash_result = code_hash
                return next
            else:
                value: StateWork_ReadContractCodeHash = last.state_work.work.value()
                key = mpt_hash(value.address)  # account addresses are hashed to get a trie key
                next = last.copy()
                next.exec_mode = ExecMode.MPTWork.value
                next.mpt_work = MPTWorkScope(
                    mode=MPTAccessMode.STARTING_READ.value,
                    tree_source=MPTTreeSource.WORLD_ACCOUNT,
                    current_root=last.state_root,
                    lookup_key=b32_to_uint256(key),
                    lookup_key_nibbles=32*2,
                    lookup_nibble_depth=0,
                )
                # we'll return to this current step, but with MPT mode set to DONE
                next.return_to_step.change(selector=1, value=last)
                return next

        if typ == StateWorkType.READ_CONTRACT_CODE:
            value: StateWork_ReadContractCode = last.state_work.work.value()

            next = last.copy()

            # We first run the code-hash retrieval, return to this step with the result + continuation mode
            next.state_work.work.change(
                selector=StateWorkType.READ_CONTRACT_CODE_HASH.value,
                value=StateWork_ReadContractCodeHash(address=value.address))
            next.state_work.mode = StateWorkMode.REQUESTING.value
            next.state_work.mode_on_finish = StateWorkMode.CONTINUE_CODE_LOOKUP.value
            next.return_to_step.change(selector=1, value=last)
            return next

        if typ == StateWorkType.REMOVE_CONTRACT_CODE:
            value: StateWork_RemoveContractCode = last.state_work.work.value()
            raise NotImplementedError
        if typ == StateWorkType.READ_NONCE:
            value: StateWork_ReadNonce = last.state_work.work.value()
            raise NotImplementedError
        if typ == StateWorkType.SET_NONCE:
            value: StateWork_SetNonce = last.state_work.work.value()
            raise NotImplementedError
        if typ == StateWorkType.STORAGE_READ:
            value: StateWork_StorageRead = last.state_work.work.value()
            raise NotImplementedError
        if typ == StateWorkType.STORAGE_WRITE:
            value: StateWork_StorageWrite = last.state_work.work.value()
            raise NotImplementedError
    if mode == StateWorkMode.CONTINUE_CODE_LOOKUP:
        value: StateWork_ReadContractCodeHash = last.state_work.work.value()
        code_hash = value.code_hash_result
        code: Code
        if code_hash == Bytes32():
            code = Code()  # empty code if hash is 0
        else:
            code_bytes = trac.code_lookup(code_hash)
            code = Code(code_bytes)  # represent as SSZ, merkleizes it
        caller = last.return_to_step.value()
        next: Step = caller.copy()
        next.state_work.mode = last.state_work.mode_on_finish
        next.state_work.work.change(
            selector=StateWorkType.READ_CONTRACT_CODE.value,
            value=StateWork_ReadContractCode(address=value.address, code_hash_result=code_hash, code=code))
        return next

    raise NotImplementedError
