import rlp
from .step import Step, Address, Bytes32, Code
from .exec_mode import ExecMode


def load_tx(step: Step, tx_bytes: bytes):
    # eip-2718: each transaction has a type
    tx_envelope_byte = tx_bytes[0]
    if not (0xc0 <= tx_envelope_byte <= 0xfe):
        tx_bytes = tx_bytes[1:]  # strip envelop byte if legacy

    # check if legacy tx
    if tx_envelope_byte == 0 or 0xc0 <= tx_envelope_byte <= 0xfe:
        # TODO parse legacy transaction
        tx_data = rlp.decode(tx_bytes)
        nonce, gas_price, gas_limit, to, value, data, v, r, s = tx_data
        # TODO: parse all of the above into tx state machine
        step.exec_mode = ExecMode.TxLoad
        return step
    elif tx_envelope_byte == 1:
        # todo parse EIP 2930 transaction
        tx_data = rlp.decode(tx_bytes[1:])
        chain_id, nonce, gas_price, gas_limit, to, value, data, access_list, signature_y_parity, signature_r, signature_s = tx_data
        step.exec_mode = ExecMode.TxLoad
        return step
    elif tx_envelope_byte == 2:
        tx_data = rlp.decode(tx_bytes[1:])
        # todo parse EIP 1559 (incl. access list like EIP 2930) transaction
        chain_id, nonce, max_priority_fee_per_gas, max_fee_per_gas, gas_limit, destination, amount, data, access_list, signature_y_parity, signature_r, signature_s = tx_data
        step.exec_mode = ExecMode.TxLoad
        return step
    else:
        step.exec_mode = ExecMode.ErrInvalidTransactionType
        return step

