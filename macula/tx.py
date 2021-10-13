import rlp
from typing import Optional
from . import keccak_256, ecrecover, validate_signature_values
from .step import Step, uint8, Bytes32, Address, CallWorkScope, CallMode, NormalizedTransaction, AccessListEntry, uint64, uint256, OpaqueTransaction, RollupSystemTransaction
from .trace import StepsTrace
from .exec_mode import ExecMode
from .params import CHAIN_ID


def exec_tx_load(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()

    opaque_tx: OpaqueTransaction = last.payload.transactions[last.tx.tx_index]

    tx_bytes = bytes(opaque_tx)

    # eip-2718: each transaction has a type
    tx_envelope_byte = tx_bytes[0]

    # normalization taken from EIP-1559 pseudocode

    # check if legacy tx
    if 0xc0 <= tx_envelope_byte <= 0xfe:
        tx_data = rlp.decode(tx_bytes)
        nonce, gas_price, gas_limit, to, value, data, v, r, s = tx_data
        # TODO: compute tx hash
        # TODO: verify signature

        next.exec_mode = ExecMode.TxSig

        # TODO ecrecover
        sender = Address()

        next.tx.current_tx_normalized = NormalizedTransaction(
            signer_address=sender,
            signer_nonce=uint64(nonce),
            gas_limit=uint64(gas_limit),
            max_priority_fee_per_gas=uint256(gas_price),
            max_fee_per_gas=uint256(gas_price),
            destination=Address(to),
            amount=uint256(value),
            payload=data,
            access_list=[],
        )

        return next
    elif tx_envelope_byte == 1:
        # todo parse EIP 2930 transaction
        tx_data = rlp.decode(tx_bytes[1:])
        chain_id, nonce, gas_price, gas_limit, to, value, data, access_list, signature_y_parity, signature_r, signature_s = tx_data

        if chain_id != CHAIN_ID:
            next.exec_mode = ExecMode.ErrInvalidTransactionChainId
            return next

        # TODO: compute tx hash
        # TODO: verify signature with chainid

        # TODO ecrecover
        sender = Address()

        next.tx.current_tx_normalized = NormalizedTransaction(
            signer_address=sender,
            signer_nonce=uint64(nonce),
            gas_limit=uint64(gas_limit),
            max_priority_fee_per_gas=uint256(gas_price),
            max_fee_per_gas=uint256(gas_price),
            destination=Address(to),
            amount=uint256(value),
            payload=data,
            access_list=[
                AccessListEntry(
                    address=Address(address),
                    storage_keys=storage_keys,
                ) for (address, storage_keys) in access_list],
        )

        next.exec_mode = ExecMode.TxSig
        return next
    elif tx_envelope_byte == 2:
        tx_data = rlp.decode(tx_bytes[1:])

        chain_id, nonce, max_priority_fee_per_gas, max_fee_per_gas, gas_limit, destination, amount, data, access_list, signature_y_parity, signature_r, signature_s = tx_data

        if chain_id != CHAIN_ID:
            next.exec_mode = ExecMode.ErrInvalidTransactionChainId
            return next

        # TODO: optimization: should be able to just take a slice of the original tx_data, and wrap with different prefix + rlp length prefix
        msg_data = bytes([tx_envelope_byte]) + rlp.encode(chain_id, nonce, max_priority_fee_per_gas, max_fee_per_gas, gas_limit, destination, amount, data)
        msg_hash = keccak_256(msg_data)

        # DynamicFee txs are defined to use 0 and 1 as their recovery
        # id, add 27 to become equivalent to unprotected Homestead signatures.
        v = signature_y_parity + 27
        signer, exec_err = recover_plain(msg_hash, signature_r, signature_s, v, True)
        if exec_err is not None:
            next.exec_mode = exec_err
            return next

        next.tx.current_tx_normalized = NormalizedTransaction(
            signer_address=signer,
            signer_nonce=uint64(nonce),
            gas_limit=uint64(gas_limit),
            max_priority_fee_per_gas=uint256(max_priority_fee_per_gas),
            max_fee_per_gas=uint256(max_fee_per_gas),
            destination=Address(destination),
            amount=uint256(amount),
            payload=data,
            access_list=[
                AccessListEntry(
                    address=Address(address),
                    storage_keys=storage_keys,
                ) for (address, storage_keys) in access_list],
        )

        next.exec_mode = ExecMode.TxSig
        return next
    elif tx_envelope_byte == 42:
        # big-endian SSZ encoded tx instead of RLP encoded.
        sys_tx = RollupSystemTransaction.decode_bytes(tx_bytes)

        # TODO: prepare EVM state

        # jump straight into the interpreter, no signature or fees to process.
        next.exec_mode = ExecMode.OpcodeLoad
        return next

    else:
        next.exec_mode = ExecMode.ErrInvalidTransactionType
        return next


def recover_plain(sighash: Bytes32, R: uint256, S: uint256, Vb: uint256, homestead: bool) -> (Address, Optional[ExecMode]):
    if Vb.bit_length() > 8:
        return Address(), ExecMode.ErrInvalidTransactionSig

    # under/overflow is part of this logic. bit-length is checked for uint8, but underflow is still valid.
    V = uint8((uint64(Vb) + 256 - 27) % 256)
    if not validate_signature_values(V, R, S, homestead):
        return Address(), ExecMode.ErrInvalidTransactionSig

    # encode the signature in uncompressed format
    r, s = R.encode_bytes(), S.encode_bytes()  # big-endian
    # concatenate the bytes; 32 + 32 + 1 = 65
    sig = r + s + bytes([V])

    # recover the public key from the signature
    pub, ok = ecrecover(sighash[:], sig)
    if not ok:
        return Address(), ExecMode.ErrInvalidTransactionSig

    if len(pub) == 0 or pub[0] != 4:
        return Address(), ExecMode.ErrInvalidTransactionPubkey

    return Address(keccak_256(pub[1:])[12:]), None


# TODO: signature check, sender address recovery

# TODO: origin balance check for fee payment and value transfer


def exec_tx_start(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()

    # TODO: more init/reset work to do
    # next.call_work = CallWorkScope(
    #     mode=CallMode.START,
    #     caller=sender,
    #     code_addr=to,
    #     read_only=False,
    #     gas=gas_limit,
    #     addr=sender,
    #     value=value,
    #     # input_offset: uint256
    #     # input_size: uint256
    #     # return_offset: uint256
    #     # return_size: uint256
    # )
