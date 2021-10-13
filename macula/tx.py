import rlp
from typing import Optional
from . import keccak_256, ecrecover, validate_signature_values
from .step import Step, uint8, Bytes32, Address, CallWorkScope, CallMode, TxMode, NormalizedTransaction, AccessListEntry, uint64, uint256, OpaqueTransaction, RollupSystemTransaction
from .trace import StepsTrace
from .exec_mode import ExecMode
from .params import CHAIN_ID, TX_ACCESS_LIST_ADDRESS_GAS, TX_ACCESS_LIST_STORAGE_KEY_GAS, TX_DATA_ZERO_GAS, TX_DATA_NON_ZERO_GAS_FRONTIER, TX_DATA_NON_ZERO_GAS_EIP2028, TX_GAS, TX_GAS_CONTRACT_CREATION


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

        is_contract_creation = False
        if len(to) != 20:
            if len(to) != 0:
                next.exec_mode = ExecMode.ErrInvalidTransactionDest
                return next

            to = b"\x00" * 20
            is_contract_creation = True

        # TODO ecrecover
        sender = Address()

        next.tx.current_tx_normalized = NormalizedTransaction(
            signer_address=sender,
            signer_nonce=uint64(nonce),
            gas_limit=uint64(gas_limit),
            max_priority_fee_per_gas=uint256(gas_price),
            max_fee_per_gas=uint256(gas_price),
            destination=Address(to),
            is_contract_creation=is_contract_creation,
            amount=uint256(value),
            payload=data,
            access_list=[],
        )

        next.exec_mode = ExecMode.TxProc
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

        is_contract_creation = False
        if len(to) != 20:
            if len(to) != 0:
                next.exec_mode = ExecMode.ErrInvalidTransactionDest
                return next

            to = b"\x00" * 20
            is_contract_creation = True

        # TODO ecrecover
        sender = Address()

        next.tx.current_tx_normalized = NormalizedTransaction(
            signer_address=sender,
            signer_nonce=uint64(nonce),
            gas_limit=uint64(gas_limit),
            max_priority_fee_per_gas=uint256(gas_price),
            max_fee_per_gas=uint256(gas_price),
            destination=Address(to),
            is_contract_creation=is_contract_creation,
            amount=uint256(value),
            payload=data,
            access_list=[
                AccessListEntry(
                    address=Address(address),
                    storage_keys=storage_keys,
                ) for (address, storage_keys) in access_list],
        )

        next.exec_mode = ExecMode.TxProc
        return next
    elif tx_envelope_byte == 2:
        tx_data = rlp.decode(tx_bytes[1:])

        chain_id, nonce, max_priority_fee_per_gas, max_fee_per_gas, gas_limit, destination, amount, data, access_list, signature_y_parity, signature_r, signature_s = tx_data

        if chain_id != CHAIN_ID:
            next.exec_mode = ExecMode.ErrInvalidTransactionChainId
            return next

        is_contract_creation = False
        if len(destination) != 20:
            if len(destination) != 0:
                next.exec_mode = ExecMode.ErrInvalidTransactionDest
                return next

            destination = b"\x00" * 20
            is_contract_creation = True

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
            is_contract_creation=is_contract_creation,
            amount=uint256(amount),
            payload=data,
            access_list=[
                AccessListEntry(
                    address=Address(address),
                    storage_keys=storage_keys,
                ) for (address, storage_keys) in access_list],
        )

        next.exec_mode = ExecMode.TxProc
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


def tx_work_proc(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()

    mode = TxMode(last.tx.mode)

    if mode == TxMode.CHECK_NONCE:
        # TODO
        next.tx.mode = TxMode.CHECK_BALANCE
        return next
    if mode == TxMode.CHECK_BALANCE:
        # TODO
        next.tx.mode = TxMode.CHECK_GAS_AVAILABLE
        return next
    if mode == TxMode.CHECK_GAS_AVAILABLE:
        # TODO
        next.tx.mode = TxMode.CHECK_INTRINSIC_GAS
        return next
    if mode == TxMode.CHECK_INTRINSIC_GAS:
        # TODO
        next.tx.mode = TxMode.CHECK_INTRINSIC_GAS_OVERFLOW
        return next
    if mode == TxMode.CHECK_INTRINSIC_GAS_OVERFLOW:
        # TODO
        next.tx.mode = TxMode.CHECK_TOPMOST_TRANSFER
        return next
    if mode == TxMode.CHECK_TOPMOST_TRANSFER:
        # TODO
        next.tx.mode = TxMode.SETUP_APPLY_TX
    if mode == TxMode.SETUP_APPLY_TX:
        if last.tx.current_tx_normalized.is_contract_creation:
            # TODO create work to do
            next.exec_mode = ExecMode.CreateSetup
        else:

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

            next.exec_mode = ExecMode.CallSetup
        return next


def intrinsic_gas(data: bytes, accessList: list, isContractCreation: bool,
                  isHomestead: bool, isEIP2028: bool) -> (uint64, Optional[ExecMode]):
    # Set the starting gas for the raw transaction
    gas: uint64
    if isContractCreation and isHomestead:
        gas = TX_GAS_CONTRACT_CREATION
    else:
        gas = TX_GAS

    # Bump the required gas by the amount of transactional data
    if len(data) > 0:
        # Zero and non-zero bytes are priced differently
        nz = uint64(0)
        for byt in data:
            if byt != 0:
                nz += 1

        # Make sure we don't exceed uint64 for all data combinations
        nonZeroGas = TX_DATA_NON_ZERO_GAS_FRONTIER
        if isEIP2028:
            nonZeroGas = TX_DATA_NON_ZERO_GAS_EIP2028

        if (0xFFFF_FFFF_FFFF_FFFF-gas)/nonZeroGas < nz:
            return 0, ExecMode.ErrGasUintOverflow

        gas += nz * nonZeroGas

        z = uint64(len(data)) - nz
        if (0xFFFF_FFFF_FFFF_FFFF-gas)/params.TxDataZeroGas < z:
            return 0, ExecMode.ErrGasUintOverflow

        gas += z * TX_DATA_ZERO_GAS

    if len(accessList) > 0:
        gas += uint64(len(accessList)) * TX_ACCESS_LIST_ADDRESS_GAS
        total_storage_keys = uint64(sum(len(storage_keys) for addr, storage_keys in accessList))
        gas += total_storage_keys * TX_ACCESS_LIST_STORAGE_KEY_GAS

    return gas, None

