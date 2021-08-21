from .trace import StepsTrace
from .step import *


def rlp_decode_list(data: bytes) -> list:
    return []  # TODO


def mpt_hash(data: bytes) -> Bytes32:
    return Bytes32()  # TODO


# 2-item nodes:
# - leaf A 2-item node [ encodedPath, value ]
# - extension A 2-item node [ encodedPath, key ]
#
# The first nibble of the encodedPath is defined as:
#
# hex char    bits    |    node type partial     path length
# ----------------------------------------------------------
# 0        0000    |       extension              even
# 1        0001    |       extension              odd
# 2        0010    |   terminating (leaf)         even
# 3        0011    |   terminating (leaf)         odd


# TODO: init claim with mpt_current_root set to state-root (or account storage root)
def next_mpt_step(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    mpt_mode = last.mpt_mode

    # TODO: define flag to switch between global/account work
    if last.mpt_global:
        trie = trac.world_accounts()
    else:
        trie = trac.account_storage(last.mpt_address_target)

    if mpt_mode == 0:  # do we have a claim to expand?
        # If yes, then expand it
        data = trie.get_node(last.mpt_current_root)
        # check that the provided MPT node witness data matches the request node root
        assert mpt_hash(data) == next.mpt_current_root

        data_li = rlp_decode_list(data)
        if len(data_li) == 0:
            next.mpt_current_root = Bytes32()
            # stop recursing deeper
            next.mpt_mode = 1

        elif len(data_li) == 2:
            encoded_path = data_li[0]  # path is the first value of the tuple, regardless of extension/leaf type choice
            assert len(encoded_path) >= 1

            # TODO: left or right 4 bytes?
            first_nibble = encoded_path[0] & 0x0f
            assert first_nibble < 4
            if first_nibble == 0:  # even length extension path
                # strip even-length nibble key prefix from key, and check it against our local key
                prefix = encoded_path[1:]
                # validate prefix
                assert last.mpt_lookup_depth + len(prefix) * 2 <= 32 * 2
                assert prefix == last.mpt_lookup_key[last.mpt_lookup_depth:last.mpt_lookup_depth + len(prefix)]
                # strip prefix from the key that we use for the next lookup
                next.mpt_lookup_key = last.mpt_lookup_key[len(prefix):]
                # continue from this deeper node (2nd value of the extension tuple)
                next.mpt_current_root = data_li[1]  # TODO: does this RLP value need decoding?
                next.mpt_lookup_depth += len(prefix) * 2
                # stay in MPT mode 0, this is another claim to expand
                return next
            if first_nibble == 1:  # odd length extension path
                # strip odd-length nibble key prefix from key, and check it against our local key
                prefix = encoded_path[
                         1:]  # TODO: this is not right, need to split the nibble, not the byte, but which nibble?

                assert last.mpt_lookup_depth + len(prefix) * 2 - 1 <= 32 * 2
                # TODO: nibble alignment not right
                assert prefix == last.mpt_lookup_key[last.mpt_lookup_depth:last.mpt_lookup_depth + len(prefix)]

                # continue from this deeper node (2nd value of the extension tuple)
                next.mpt_current_root = data_li[1]  # TODO: does this RLP value need decoding?
                next.mpt_lookup_depth += len(prefix) * 2 - 1
                # stay in MPT mode 0, this is another claim to expand
                return next
            if first_nibble == 2:  # even length terminating leaf node
                prefix = encoded_path[1:]
                assert last.mpt_lookup_depth + len(prefix) * 2 == 32 * 2  # key length needs to match exactly
                assert prefix == last.mpt_lookup_key[last.mpt_lookup_depth:]  # do we have the right key remainder?
                next.mpt_current_root = Bytes32()
                next.mpt_lookup_depth = 0
                next.mpt_input_rlp = data_li[1]
                # go to the MPT mode that uses the found value
                next.mpt_mode = 1
            if first_nibble == 3:  # odd length terminating leaf node
                prefix = encoded_path[
                         1:]  # TODO: this is not right, need to split the nibble, not the byte, but which nibble?

                assert last.mpt_lookup_depth + len(prefix) * 2 - 1 == 32 * 2
                # TODO: nibble alignment not right
                assert prefix == last.mpt_lookup_key[last.mpt_lookup_depth:]
                next.mpt_current_root = Bytes32()
                next.mpt_lookup_depth = 0
                next.mpt_input_rlp = data_li[1]

                # go to the MPT mode that uses the found value
                next.mpt_mode = 1
            else:
                raise Exception("invalid MPT node first nibble: %d" % first_nibble)

            # remember the path in case we go back up later
            next.encoded_path = encoded_path

        elif len(data_li) == 17:
            branch_nodes = data_li[:16]
            vt = rlp_decode_list(data_li[16])
            assert len(vt) == 0  # expected NULL for trees with keys of equal length
            key_nibble = next.mpt_lookup_key[next.mpt_lookup_depth]
            next.mpt_current_root = branch_nodes[key_nibble]  # TODO: does this need further decoding?
            next.mpt_lookup_depth += 1

        next.expanded_type = 0  # TODO: branch, extension or leaf
        next.mpt_input = data
        next.mpt_mode = 1  # we filled the claim

        # for debugging purposes: ensure we got the correct node from the DB
        # as a verifier on-chain, it is checked within the get_node function

        return next

    if mpt_mode == 1:  #
        # TODO: check if we're reading or writing
        # If reading only, return the decoded last.mpt_input_rlp
        # If writing, then based on traversal of a write-key, modify the nodes we just passed by,
        #  from bottom to top, to construct a new state root.
        # 1. modify RLP
        # 2. in step loop:
        #   2.1 fetch RLP from layer higher that we just read top-down
        #   2.2 split extension node, or overwrite slot in branch-node, to insert the key
        #   2.3 compute mpt_hash to use for next higher layer
        # 3. continue until at top, then have the resulting state-root (or root of storage in account)
        raise NotImplementedError
