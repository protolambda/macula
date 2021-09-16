import rlp
from .step import Step, Address, Bytes32, Code, Transaction, OpaqueTransaction, RollupSystemTransaction
from .trace import StepsTrace
from .exec_mode import ExecMode


def exec_tx_load(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()

    tx_union: Transaction = last.payload.transactions[last.tx.tx_index]
    consensus_tx_type = tx_union.selector()
    if consensus_tx_type == 42:
        # TODO: process deposit
        sys_tx: RollupSystemTransaction = tx_union.value()
        # TODO: prepare EVM state

        # jump straight into the interpreter, no signature or fees to process.
        next.exec_mode = ExecMode.OpcodeLoad
        return next

    if consensus_tx_type == 0:
        opaque_tx: OpaqueTransaction = tx_union.value()
        tx_bytes = bytes(opaque_tx)

        # eip-2718: each transaction has a type
        tx_envelope_byte = tx_bytes[0]
        if not (0xc0 <= tx_envelope_byte <= 0xfe):
            tx_bytes = tx_bytes[1:]  # strip envelop byte if legacy

        # TODO: EIP-1559 has pseudocode for normalizing this elegantly

        # check if legacy tx
        if tx_envelope_byte == 0 or 0xc0 <= tx_envelope_byte <= 0xfe:
            # TODO parse legacy transaction
            tx_data = rlp.decode(tx_bytes)
            nonce, gas_price, gas_limit, to, value, data, v, r, s = tx_data
            # TODO: parse all of the above into tx state machine
            next.exec_mode = ExecMode.TxSig
            return next
        elif tx_envelope_byte == 1:
            # todo parse EIP 2930 transaction
            tx_data = rlp.decode(tx_bytes[1:])
            chain_id, nonce, gas_price, gas_limit, to, value, data, access_list, signature_y_parity, signature_r, signature_s = tx_data
            next.exec_mode = ExecMode.TxSig
            return next
        elif tx_envelope_byte == 2:
            tx_data = rlp.decode(tx_bytes[1:])
            # todo parse EIP 1559 (incl. access list like EIP 2930) transaction
            chain_id, nonce, max_priority_fee_per_gas, max_fee_per_gas, gas_limit, destination, amount, data, access_list, signature_y_parity, signature_r, signature_s = tx_data
            next.exec_mode = ExecMode.TxSig
            return next
        else:
            next.exec_mode = ExecMode.ErrInvalidTransactionType
            return next

    # Other consensus transaction types are illegal / not implemented
    raise NotImplementedError

