from enum import IntEnum


class ExecMode(IntEnum):
    BlockPre = 0

    TxLoad = 0x01
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

    # Every call opcode shares a setup
    CallSetup = 0x30

    # Call pre-processing
    CallPre = 0x31

    # Any error should follow up with running call-post processing
    CallPost = 0x32

    CallRevert = 0x33

    # Sets up the state, handles errors, runs init code
    CreateSetup = 0x34
    # after init completes, create the contract
    CreateInitPost = 0x35
    CreateInitRevert = 0x36
    CreateInitErr = 0x37

    # Stops execution of a transaction
    # (block processing continues, tx is just included as "failed", and still pays the fee etc.)
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

    # These errors are more critical: the block is invalid
    ErrInvalidTransactionType = 0x50
    ErrInvalidTransactionChain = 0x51
    ErrInvalidTransactionSig = 0x52

    # Special state machines
    StateWork = 0x60
    MPTWork = 0x61

    # Block pre-state load
    BlockPreStateLoad = 0x70

    # Block preparation
    BlockHistoryLoad = 0x71

    # loads the parent block header to derive EIP-1559 base fee
    # (using previous base fee, parent gas limit, parent gas used, and target)
    BlockCalcBaseFee = 0x72

    # Loop through transactions till everything is processed
    BlockTxLoop = 0x73

    # when the transaction finishes, block tx loop continues in TxSuccess, TxErr or TxRevert
    BlockTxSuccess = 0x74
    BlockTxErr = 0x75
    BlockTxRevert = 0x76

    # when done with the block transactions
    BlockPost = 0x80

    # When completely done
    DONE = 0xff
