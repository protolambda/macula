# See geth/params/protocol_params.go

GAS_LIMIT_BOUND_DIVISOR = 1024  # The bound divisor of the gas limit, used in update calculations.
MIN_GAS_LIMIT = 5000  # Minimum the gas limit may ever be.
GENESIS_GAS_LIMIT = 4712388  # Gas limit of the Genesis block.

MAXIMUM_EXTRA_DATA_SIZE = 32  # Maximum size extra data may be after Genesis.
EXP_BYTE_GAS = 10  # Times ceil(log256(exponent)) for the EXP instruction.
SLOAD_GAS = 50  # Multiplied by the number of 32-byte words that are copied (round up) for any *COPY operation and added.
CALL_VALUE_TRANSFER_GAS = 9000  # Paid for CALL when the value transfer is non-zero.
CALL_NEW_ACCOUNT_GAS = 25000  # Paid for CALL when the destination address didn't exist prior.
TX_GAS = 21000  # Per transaction not creating a contract. NOTE: Not payable on data of calls between transactions.
TX_GAS_CONTRACT_CREATION = 53000  # Per transaction that creates a contract. NOTE: Not payable on data of calls between transactions.
TX_DATA_ZERO_GAS = 4  # Per byte of data attached to a transaction that equals zero. NOTE: Not payable on data of calls between transactions.
QUAD_COEFF_DIV = 512  # Divisor for the quadratic particle of the memory cost equation.
LOG_DATA_GAS = 8  # Per byte in a LOG* operation's data.
CALL_STIPEND = 2300  # Free gas given at beginning of call.

SHA3GAS = 30  # Once per SHA3 operation.
SHA3WORD_GAS = 6  # Once per word of the SHA3 operation's data.

SSTORE_SET_GAS = 20000  # Once per SSTORE operation.
SSTORE_RESET_GAS = 5000  # Once per SSTORE operation if the zeroness changes from zero.
SSTORE_CLEAR_GAS = 5000  # Once per SSTORE operation if the zeroness doesn't change.
SSTORE_REFUND_GAS = 15000  # Once per SSTORE operation if the zeroness changes to zero.

NET_SSTORE_NOOP_GAS = 200  # Once per SSTORE operation if the value doesn't change.
NET_SSTORE_INIT_GAS = 20000  # Once per SSTORE operation from clean zero.
NET_SSTORE_CLEAN_GAS = 5000  # Once per SSTORE operation from clean non-zero.
NET_SSTORE_DIRTY_GAS = 200  # Once per SSTORE operation from dirty.

NET_SSTORE_CLEAR_REFUND = 15000  # Once per SSTORE operation for clearing an originally existing storage slot
NET_SSTORE_RESET_REFUND = 4800  # Once per SSTORE operation for resetting to the original non-zero value
NET_SSTORE_RESET_CLEAR_REFUND = 19800  # Once per SSTORE operation for resetting to the original zero value

SSTORE_SENTRY_GAS_EIP2200 = 2300  # Minimum gas required to be present for an SSTORE call, not consumed
SSTORE_SET_GAS_EIP2200 = 20000  # Once per SSTORE operation from clean zero to non-zero
SSTORE_RESET_GAS_EIP2200 = 5000  # Once per SSTORE operation from clean non-zero to something else
SSTORE_CLEARS_SCHEDULE_REFUND_EIP2200 = 15000  # Once per SSTORE operation for clearing an originally existing storage slot

COLD_ACCOUNT_ACCESS_COST_EIP2929 = 2600  # COLD_ACCOUNT_ACCESS_COST
COLD_SLOAD_COST_EIP2929 = 2100  # COLD_SLOAD_COST
WARM_STORAGE_READ_COST_EIP2929 = 100  # WARM_STORAGE_READ_COST

TX_DATA_NON_ZERO_GAS_FRONTIER = 68  # Per byte of data attached to a transaction that is not equal to zero. NOTE: Not payable on data of calls between transactions.
TX_DATA_NON_ZERO_GAS_EIP2028 = 16  # Per byte of non zero data attached to a transaction after EIP 2028 (part in Istanbul)
TX_ACCESS_LIST_ADDRESS_GAS = 2400  # Per address specified in EIP 2930 access list
TX_ACCESS_LIST_STORAGE_KEY_GAS = 1900  # Per storage key specified in EIP 2930 access list

# In EIP-2200: Sstore_Reset_Gas was 5000.
# In EIP-2929: Sstore_Reset_Gas was changed to '5000 - COLD_SLOAD_COST'.
# In EIP-3529: SSTORE_CLEARS_SCHEDULE is defined as SSTORE_RESET_GAS + ACCESS_LIST_STORAGE_KEY_COST
# WHICH BECOMES: 5000 - 2100 + 1900 = 4800
SSTORE_CLEARS_SCHEDULE_REFUND_EIP3529 = SSTORE_RESET_GAS_EIP2200 - COLD_SLOAD_COST_EIP2929 + TX_ACCESS_LIST_STORAGE_KEY_GAS

JUMPDEST_GAS = 1  # Once per JUMPDEST operation.
EPOCH_DURATION = 30000  # Duration between proof-of-work epochs.

CREATE_DATA_GAS = 200  #
CALL_CREATE_DEPTH = 1024  # Maximum depth of call/create stack.
EXP_GAS = 10  # Once per EXP instruction
LOG_GAS = 375  # Per LOG* operation.
COPY_GAS = 3  #
STACK_LIMIT = 1024  # Maximum size of VM stack allowed.
TIER_STEP_GAS = 0  # Once per operation, for a selection of them.
LOG_TOPIC_GAS = 375  # Multiplied by the * of the LOG*, per LOG transaction. e.g. LOG0 incurs 0 * c_tx_Log_Topic_Gas, LOG4 incurs 4 * c_tx_Log_Topic_Gas.
CREATE_GAS = 32000  # Once per CREATE operation & contract-creation transaction.
CREATE2GAS = 32000  # Once per CREATE2 operation
SELFDESTRUCT_REFUND_GAS = 24000  # Refunded following a selfdestruct operation.
MEMORY_GAS = 3  # Times the address of the (highest referenced byte in memory + 1). NOTE: referencing happens on read, write and in instructions such as RETURN and CALL.

# These have been changed during the course of the chain
CALL_GAS_FRONTIER = 40  # Once per CALL operation & message call transaction.
CALL_GAS_EIP150 = 700  # Static portion of gas for CALL-derivates after EIP 150 (Tangerine)
BALANCE_GAS_FRONTIER = 20  # The cost of a BALANCE operation
BALANCE_GAS_EIP150 = 400  # The cost of a BALANCE operation after Tangerine
BALANCE_GAS_EIP1884 = 700  # The cost of a BALANCE operation after EIP 1884 (part of Istanbul)
EXTCODE_SIZE_GAS_FRONTIER = 20  # Cost of EXTCODESIZE before EIP 150 (Tangerine)
EXTCODE_SIZE_GAS_EIP150 = 700  # Cost of EXTCODESIZE after EIP 150 (Tangerine)
SLOAD_GAS_FRONTIER = 50
SLOAD_GAS_EIP150 = 200
SLOAD_GAS_EIP1884 = 800  # Cost of SLOAD after EIP 1884 (part of Istanbul)
SLOAD_GAS_EIP2200 = 800  # Cost of SLOAD after EIP 2200 (part of Istanbul)
EXTCODE_HASH_GAS_CONSTANTINOPLE = 400  # Cost of EXTCODEHASH (introduced in Constantinople)
EXTCODE_HASH_GAS_EIP1884 = 700  # Cost of EXTCODEHASH after EIP 1884 (part in Istanbul)
SELFDESTRUCT_GAS_EIP150 = 5000  # Cost of SELFDESTRUCT post EIP 150 (Tangerine)

# EXP has a dynamic portion depending on the size of the exponent
EXP_BYTE_FRONTIER = 10  # was set to 10 in Frontier
EXP_BYTE_EIP158 = 50  # was raised to 50 during Eip158 (Spurious Dragon)

# Extcodecopy has a dynamic AND a static cost. This represents only the
# static portion of the gas. It was changed during EIP 150 (Tangerine)
EXTCODE_COPY_BASE_FRONTIER = 20
EXTCODE_COPY_BASE_EIP150 = 700

# Create_By_Selfdestruct_Gas is used when the refunded account is one that does
# not exist. This logic is similar to call.
# Introduced in Tangerine Whistle (Eip 150)
CREATE_BY_SELFDESTRUCT_GAS = 25000

BASE_FEE_CHANGE_DENOMINATOR = 8  # Bounds the amount the base fee can change between blocks.
ELASTICITY_MULTIPLIER = 2  # Bounds the maximum gas limit an EIP-1559 block may have.
INITIAL_BASE_FEE = 1000000000  # Initial base fee for EIP-1559 blocks.

MAX_CODE_SIZE = 24576  # Maximum bytecode to permit for a contract

# Precompiled contract gas prices

ECRECOVER_GAS = 3000  # Elliptic curve sender recovery gas price
SHA256BASE_GAS = 60  # Base price for a SHA256 operation
SHA256PER_WORD_GAS = 12  # Per-word price for a SHA256 operation
RIPEMD160BASE_GAS = 600  # Base price for a RIPEMD160 operation
RIPEMD160PER_WORD_GAS = 120  # Per-word price for a RIPEMD160 operation
IDENTITY_BASE_GAS = 15  # Base price for a data copy operation
IDENTITY_PER_WORD_GAS = 3  # Per-work price for a data copy operation

BN256ADD_GAS_BYZANTIUM = 500  # Byzantium gas needed for an elliptic curve addition
BN256ADD_GAS_ISTANBUL = 150  # Gas needed for an elliptic curve addition
BN256SCALAR_MUL_GAS_BYZANTIUM = 40000  # Byzantium gas needed for an elliptic curve scalar multiplication
BN256SCALAR_MUL_GAS_ISTANBUL = 6000  # Gas needed for an elliptic curve scalar multiplication
BN256PAIRING_BASE_GAS_BYZANTIUM = 100000  # Byzantium base price for an elliptic curve pairing check
BN256PAIRING_BASE_GAS_ISTANBUL = 45000  # Base price for an elliptic curve pairing check
BN256PAIRING_PER_POINT_GAS_BYZANTIUM = 80000  # Byzantium per-point price for an elliptic curve pairing check
BN256PAIRING_PER_POINT_GAS_ISTANBUL = 34000  # Per-point price for an elliptic curve pairing check

BLS12381G1ADD_GAS = 600  # Price for BLS12-381 elliptic curve G1 point addition
BLS12381G1MUL_GAS = 12000  # Price for BLS12-381 elliptic curve G1 point scalar multiplication
BLS12381G2ADD_GAS = 4500  # Price for BLS12-381 elliptic curve G2 point addition
BLS12381G2MUL_GAS = 55000  # Price for BLS12-381 elliptic curve G2 point scalar multiplication
BLS12381PAIRING_BASE_GAS = 115000  # Base gas price for BLS12-381 elliptic curve pairing check
BLS12381PAIRING_PER_PAIR_GAS = 23000  # Per-point pair gas price for BLS12-381 elliptic curve pairing check
BLS12381MAP_G1GAS = 5500  # Gas price for BLS12-381 mapping field element to G1 operation
BLS12381MAP_G2GAS = 110000  # Gas price for BLS12-381 mapping field element to G2 operation

# The Refund Quotient is the cap on how much of the used gas can be refunded. Before EIP-3529,
# up to half the consumed gas could be refunded. Redefined as 1/5th in EIP-3529
REFUND_QUOTIENT = 2
REFUND_QUOTIENT_EIP3529 = 5

# TODO
CHAIN_ID = 42
