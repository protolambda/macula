from enum import Enum

class ExecMode(Enum):
    BlockPre = 0

    TxInclusion = 0x01
    TxSig = 0x02
    TxFeesPre = 0x03
    TxFeesPost = 0x04

    # Interpreter loop consists of stack/memory/gas checks, and then opcode execution.
    OpcodeLoad = 0x11
    ValidateStack = 0x12
    ReadOnlyCheck = 0x13
    ConstantGas = 0x14
    CalcMemorySize = 0x15
    DynamicGas = 0x16
    UpdateMemorySize = 0x17
    # when done running, continue with ExecOpcodeLoad. Or any error
    OpcodeRun = 0x18

    # Call pre-processing (increment call depth)
    CallPre = 0x30

    # Any error should follow up with running call-post processing
    CallPost = 0x30

    # Stops execution
    ErrSTOP = 0x40
    ErrStackUnderflow = 0x41
    ErrStackOverflow = 0x42
    ErrWriteProtection = 0x43
    ErrOutOfGas = 0x44
    ErrGasUintOverflow = 0x45
    ErrInvalidJump = 0x46
    ErrReturnDataOutOfBounds = 0x47
    ErrDepth = 0x48
    ErrInsufficientBalance = 0x49
    ErrExecutionReverted = 0x4a

    # Special state machines
    StateWork = 0x50
    MPTWork = 0x51

    # When completely done, and the tx was applied successfully
    Success = 0xff


# incl. start, incl. end
exec_mode_err_range = (0x40, 0x4f)


def exec_is_done(mode: ExecMode) -> bool:
    return mode == ExecMode.Success or (exec_mode_err_range[0] <= mode.value <= exec_mode_err_range[1])
