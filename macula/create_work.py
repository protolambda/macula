from .step import Step, CreateMode
from .trace import StepsTrace
from .exec_mode import ExecMode


def create_work_setup_proc(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()

    mode = CreateMode(last.create_work.mode)

    # The create1 entrypoint
    if mode == CreateMode.START_CREATE:
        next.create_work.mode = CreateMode.GET_CALLER_NONCE
        return next
    if mode == CreateMode.GET_CALLER_NONCE:
        next.create_work.mode = CreateMode.COMPUTE_CREATE_CODE_HASH
        return next
    if mode == CreateMode.COMPUTE_CREATE_CODE_HASH:
        next.create_work.mode = CreateMode.CREATE_DEPTH_CHECK
        return next

    # The create2 entrypoint
    if mode == CreateMode.START_CREATE2:
        next.create_work.mode = CreateMode.COMPUTE_CREATE2_CODE_HASH
        return next
    if mode == CreateMode.COMPUTE_CREATE2_CODE_HASH:
        next.create_work.mode = CreateMode.CREATE_DEPTH_CHECK
        return next

    if mode == CreateMode.CREATE_DEPTH_CHECK:
        # TODO
        next.create_work.mode = CreateMode.LOAD_INIT_CODE
        return next
    if mode == CreateMode.LOAD_INIT_CODE:
        # TODO
        next.create_work.mode = CreateMode.READ_BALANCE
        return next
    if mode == CreateMode.READ_BALANCE:
        # TODO
        next.create_work.mode = CreateMode.CHECK_TRANSFER_VALUE
        return next
    if mode == CreateMode.CHECK_TRANSFER_VALUE:
        # TODO
        next.create_work.mode = CreateMode.INCREMENT_NONCE
        return next
    if mode == CreateMode.INCREMENT_NONCE:
        # TODO
        next.create_work.mode = CreateMode.ADD_TO_ACCESS_LIST
        return next
    if mode == CreateMode.ADD_TO_ACCESS_LIST:
        # TODO
        next.create_work.mode = CreateMode.CHECK_CONTRACT_ALREADY_EXISTS
        return next
    if mode == CreateMode.CHECK_CONTRACT_ALREADY_EXISTS:
        # TODO
        next.create_work.mode = CreateMode.SNAPSHOT
        return next
    if mode == CreateMode.SNAPSHOT:
        # TODO
        next.create_work.mode = CreateMode.CREATE_ACCOUNT
        return next
    if mode == CreateMode.CREATE_ACCOUNT:
        # TODO
        next.create_work.mode = CreateMode.TRANSFER_VALUE
        return next
    if mode == CreateMode.TRANSFER_VALUE:
        # TODO
        next.create_work.mode = CreateMode.PREPARE_INIT_CALL
        return next
    if mode == CreateMode.PREPARE_INIT_CALL:
        # TODO
        next.create_work.mode = CreateMode.RUN_INIT_CONTRACT
        return next
    if mode == CreateMode.RUN_INIT_CONTRACT:
        # TODO start call
        # next.call_work = CallWorkScope(
        #     mode=CallMode.START,  # TODO: maybe skip some things that create doesn't do?
        #     caller=caller,
        #     code_addr=addr,
        #     read_only=last.contract.read_only,  # inherit readonly mode
        #     gas=gas,
        #     addr=addr,
        #     value=value,
        #     input_offset=input_offset,
        #     input_size=input_size,
        #     return_offset=return_offset,
        #     return_size=return_size,
        # )
        next.exec_mode = ExecMode.CallSetup
        return next

    raise NotImplementedError


def create_work_post_proc(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()

    mode = CreateMode(last.create_work.mode)
    if mode == CreateMode.RUN_INIT_CONTRACT:
        next.create_work.mode = CreateMode.CHECK_CODE_SIZE
        return next

    if mode == CreateMode.CHECK_CODE_SIZE:
        # TODO
        next.create_work.mode = CreateMode.CHECK_CODE_STARTING_BYTE
        return next
    if mode == CreateMode.CHECK_CODE_STARTING_BYTE:
        # TODO
        next.create_work.mode = CreateMode.USE_CREATE_GAS
        return next
    if mode == CreateMode.USE_CREATE_GAS:
        # TODO
        next.create_work.mode = CreateMode.SET_ACCOUNT_CODE
        return next
    if mode == CreateMode.SET_ACCOUNT_CODE:
        if last.contract.call_depth <= 1:
            next.exec_mode == ExecMode.BlockTxSuccess
        else:
            # continue execution
            next.exec_mode = ExecMode.OpcodeLoad
        return next

    raise NotImplementedError


def create_work_revert_proc(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()

    raise NotImplementedError


def create_work_err_proc(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()

    raise NotImplementedError
