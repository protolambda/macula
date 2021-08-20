from enum import Enum

class ExecMode(Enum):
    BlockPre = 0

    TxInclusion = 0x01
    TxSig = 0x02
    TxFeesPre = 0x03
    TxFeesPost = 0x04

    # Call pre-processing (increment call depth)
    CallPre = 0x30

    # Any error should follow up with running call-post processing
    CallPost = 0x30

    # Interpreter loop consists of stack/memory/gas checks, and then opcode execution.
    OpcodeLoad = 0x11
    ValidateStack = 0x12
    ReadOnlyCheck = 0x13
    ConstantGas = 0x14
    CalcMemorySize = 0x15
    DynamicGas = 0x26
    UpdateMemorySize = 0x27
    # when done running, continue with ExecOpcodeLoad. Or any error
    OpcodeRun = 0x28

    # Stops execution
    ErrSTOP = 0x40
    ErrStackUnderflow = 0x41
    ErrStackOverflow = 0x42
    ErrWriteProtection = 0x43
    ErrOutOfGas = 0x44
    ErrGasUintOverflow = 0x45
    ErrInvalidJump = 0x46

exec_mode_err_range = (0x40, 0x4f)
