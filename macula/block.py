from .exec_mode import ExecMode
from . import keccak_256
from .step import Step, MinimalExecutionPayload, Bytes32
from .trace import StepsTrace
from rlp import decode_lazy
from .params import INITIAL_BASE_FEE, ELASTICITY_MULTIPLIER, BASE_FEE_CHANGE_DENOMINATOR


def load_block(payload: MinimalExecutionPayload) -> Step:

    return Step(
        # TODO: in the future maybe load multiple payloads this way, and go through multiple blocks in trace.
        payload=payload,
        # the pre-state-root is part of the parent hash and is loaded later.
        exec_mode=ExecMode.BlockPre,
        # all other values left to default. Easy to initialize the step on-chain.
        # The trace execution will take care of further loading the payload into the Step
    )


def exec_pre_block(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    sub_index = last.sub_index

    # step by step, fully copy over the payload into the right places
    if sub_index == 0:
        next.block.parent_hash = last.payload.parent_hash
    elif sub_index == 1:
        next.block.coinbase = last.payload.coinbase
    elif sub_index == 2:
        next.block.difficulty = last.payload.random
    elif sub_index == 3:
        next.block.block_number = last.payload.block_number
    elif sub_index == 4:
        next.block.gas_limit = last.payload.gas_limit
    elif sub_index == 5:
        next.block.time = last.payload.timestamp
    else:
        # note: we don't have to move the transactions, the step.tx.tx_index == 0, and it will load later.
        # Continue with loading pre-state
        next.exec_mode = ExecMode.BlockPreStateLoad
        next.sub_index = 0
        return next

    next.sub_index += 1
    return next


def exec_block_pre_state_load(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()

    parent_hash = last.payload.parent_hash
    parent_header_rlp = trac.block_header(parent_hash)

    # verify it matches
    if keccak_256(parent_header_rlp) != parent_hash:
        raise Exception("parent witness is invalid for hash %s" % parent_hash.hex())

    # extract the state-root of the parent block, this will be the pre state root
    lazy = decode_lazy(parent_header_rlp)
    next.state_root = lazy[3]

    next.exec_mode = ExecMode.BlockHistoryLoad
    return next


def exec_block_history_load(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()

    sub_index = last.sub_index
    if sub_index < 256:
        # Block hashes are put in the buffer of 256 hashes, based on their absolute block number.
        # The current hash is not available yet, instead it carries the 256th hash there.
        dest = (last.block.block_number + 255 - sub_index) % 256
        if sub_index == 0:  # base case: load parent hash
            next.history.block_hashes[dest] = last.payload.parent_hash
        elif sub_index > last.block.block_number:
            # we reached genesis, just load zero hashes instead
            next.history.block_hashes[dest] = Bytes32()
        else:
            prev_hash: Bytes32 = last.history.block_hashes[(dest+255) % 256]  # get previous block hash
            parent_header_rlp = trac.block_header(prev_hash)
            # verify it matches, stop fraud proof execution if not.
            # (witness data is invalid, but both parties agreed on it,
            # thus any of the two they need to run again but with proper witness data)
            if keccak_256(parent_header_rlp) != prev_hash:
                raise Exception("parent witness is invalid for hash %s" % prev_hash.hex())

            # the parent-hash is the first RLP element. Don't have to decode the rest.
            parent_hash = decode_lazy(parent_header_rlp)[0]
            next.history.block_hashes[dest] = parent_hash
        next.sub_index += 1
        return next
    else:
        # completed load of all parent hashes!
        # kindly reset the sub-index
        next.sub_index = 0
        # continue with calculating the current base fee.
        next.exec_mode = ExecMode.BlockBaseFee
        return next


def exec_block_calc_base_fee(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    # based on the previous block base fee
    parent_hash = last.payload.parent_hash
    parent_header_rlp = trac.block_header(parent_hash)

    # verify it matches
    if keccak_256(parent_header_rlp) != parent_hash:
        raise Exception("parent witness is invalid for hash %s" % parent_hash.hex())

    # Block header RLP fields (TODO: double check):
    # 0 parentHash
    # 1 sha3Uncles
    # 2 miner
    # 3 stateRoot
    # 4 transactionsRoot
    # 5 receiptsRoot
    # 6 logsBloom
    # 7 difficulty
    # 8 number
    # 9 gasLimit
    # 10 gasUsed
    # 11 timestamp
    # 12 extraData
    # 13 baseFeePerGas
    lazy = decode_lazy(parent_header_rlp)
    parent_gas_limit = lazy[9]
    parent_gas_used = lazy[10]
    parent_base_fee_per_gas = lazy[13]

    # Copy-pasta from the EIP-1559 spec
    parent_gas_target = parent_gas_limit // ELASTICITY_MULTIPLIER
    if last.block.block_number == 0:  # EIP-1559 always effective from the start
        expected_base_fee_per_gas = INITIAL_BASE_FEE
    elif parent_gas_used == parent_gas_target:
        expected_base_fee_per_gas = parent_base_fee_per_gas
    elif parent_gas_used > parent_gas_target:
        gas_used_delta = parent_gas_used - parent_gas_target
        base_fee_per_gas_delta = max(parent_base_fee_per_gas * gas_used_delta // parent_gas_target // BASE_FEE_CHANGE_DENOMINATOR, 1)
        expected_base_fee_per_gas = parent_base_fee_per_gas + base_fee_per_gas_delta
    else:
        gas_used_delta = parent_gas_target - parent_gas_used
        base_fee_per_gas_delta = parent_base_fee_per_gas * gas_used_delta // parent_gas_target // BASE_FEE_CHANGE_DENOMINATOR
        expected_base_fee_per_gas = parent_base_fee_per_gas - base_fee_per_gas_delta

    next.block.base_fee = expected_base_fee_per_gas
    next.exec_mode = ExecMode.BlockTxLoop
    return next


def exec_block_tx_loop(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()

    tx_index = last.tx.tx_index
    # any transactions left? Then load it (it will return back to TxLoop execution mode)
    if len(last.payload.transactions) > tx_index:
        # Note: no large copy, just the root of the sub-tree, so we can avoid dynamic access later
        next.tx.current_tx = last.payload.transactions[tx_index]
        next.exec_mode = ExecMode.TxLoad
        return next
    else:
        # if not, then start block post processing
        next.exec_mode = ExecMode.BlockPost
        return next


def exec_post_block(trac: StepsTrace) -> Step:
    # See EIP-1559 for block validation python code
    # TODO We need to validate gas limits at the end of block execution.
    # And not at the start, since we cannot trust, and thus not know, the gas-used number of this block before execution

    # # check if the block used too much gas
    # assert block.gas_used <= block.gas_limit, 'invalid block: too much gas used'
    #
    # # check if the block changed the gas limit too much
    # assert block.gas_limit < parent_gas_limit + parent_gas_limit // 1024, 'invalid block: gas limit increased too much'
    # assert block.gas_limit > parent_gas_limit - parent_gas_limit // 1024, 'invalid block: gas limit decreased too much'
    #
    # # check if the gas limit is at least the minimum gas limit
    # assert block.gas_limit >= 5000
    ...
    last = trac.last()
    next = last.copy()

    # TODO: compute the block hash

    # TODO: reconstruct the full ExecutionPayload,
    #  that nicely summarizes the execution with a binary-tree commitment,
    #  and can be used on L1 for more efficient state root proofs
    #  (it contains both block hash and state-root, so no RLP necessary on L1)

    next.exec_mode = ExecMode.DONE
    return next
