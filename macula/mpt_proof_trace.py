from .trace import StepsTrace, Processor, MPT
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

def strip_nibble(v: uint256) -> uint256:
    return v >> 4


def read_nibble(v: uint256, i: int) -> int:
    return (int(v) >> (i*4)) & 0x0F


def decode_path(encoded_path: bytes) -> (bool, uint256, int):
    if len(encoded_path) == 0:
        return 0, 0, 0
    assert len(encoded_path) <= 32 + 1  # keys are at most 32 bytes in ethereum, even though MPT supports any length
    flag_nibble = (encoded_path[0] & 0xF0) >> 4
    terminating = flag_nibble & 0b0010 != 0
    evenlen = flag_nibble & 0b0001 == 0
    assert flag_nibble & 0b1100 == 0
    path_u256 = uint256(int.from_bytes(encoded_path[1:].ljust(32), byteorder='big'))
    path_nibble_len = len(encoded_path[1:]) * 2
    if not evenlen:  # if odd, then the 4 bits "after" (when hex encoded) the flag bits are part of the path
        assert path_nibble_len < 32
        path_u256 >>= 4
        path_u256 |= uint256(encoded_path[0] & 0x0F) << (256 - 4)
        path_nibble_len += 1
    return terminating, path_u256, path_nibble_len


def make_reader_step_gen(trie: MPT) -> Processor:
    def reader_step_gen(trac: StepsTrace) -> Step:
        last = trac.last()
        next = last.copy()

        if last.mpt_lookup_key_nibbles == last.mpt_lookup_nibble_depth:  # have we arrived yet?
            if len(last.mpt_current_root) < 32:
                value = last.mpt_current_root
            else:
                value = trie.get_node(last.mpt_current_root)
                assert mpt_hash(value) == next.mpt_current_root
            next.mpt_value = value
            next.mpt_mode = last.mpt_mode_on_finish
            return next

        # If not arrived yet, then expand it
        data = trie.get_node(last.mpt_current_root)
        # check that the provided MPT node witness data matches the request node root
        assert mpt_hash(data) == next.mpt_current_root

        data_li = rlp_decode_list(data)
        if len(data_li) == 0:
            next.mpt_current_root = Bytes32()
            # stop recursing deeper, null value
            next.mpt_value = b""
            next.mpt_mode = last.mpt_mode_on_finish
            return next

        elif len(data_li) == 2:
            encoded_path = data_li[0]  # path is the first value of the tuple, regardless of extension/leaf type choice
            assert len(encoded_path) >= 1
            terminating, path_u256, path_nibble_len = decode_path(encoded_path)

            if terminating:  # handle leaf
                key_remainder = last.mpt_lookup_key << (last.mpt_lookup_nibble_depth*4)
                # ensure we have the right key remainder
                assert key_remainder == path_u256
                new_depth = last.mpt_lookup_nibble_depth + path_nibble_len
                assert new_depth == last.mpt_lookup_key_nibbles  # check we have read the full key
                next.mpt_lookup_nibble_depth = new_depth

                # it's a leaf, but we'll expand it if it was hashed (>= 32 bytes)
                next.mpt_current_root = data_li[1]

                # stay in MPT mode 0, this is a new mpt_current_root to expand
                return next
            else:  # handle extension
                key_remainder = last.mpt_lookup_key << (last.mpt_lookup_nibble_depth*4)
                # mask out the part of the key that should match this entry
                mask = (uint256(1) << (path_nibble_len*4)) - 1
                shifted_mask = mask << (256 - path_nibble_len*4)
                key_part = key_remainder & shifted_mask
                assert key_part == path_u256
                new_depth = last.mpt_lookup_nibble_depth + path_nibble_len
                # full key may be read if we extend to a branch node that has mixed-length keys,
                #  one at 0, in the vt slot
                assert new_depth <= last.mpt_lookup_key_nibbles
                next.mpt_lookup_nibble_depth = new_depth
                # the value of the extension will be the next hashed node to expand into
                next.mpt_current_root = data_li[1]
                # stay in MPT mode 0, this is a new mpt_current_root to expand
                return next

        elif len(data_li) == 17:
            branch_nodes = data_li
            assert len(branch_nodes) == 17

            if last.mpt_lookup_nibble_depth == last.mpt_lookup_key_nibbles:
                # we arrived at the key depth already, there are other nodes with longer keys,
                # but we only care about the vt node (17th of branch)
                next.mpt_current_root = branch_nodes[16]
                # stay in MPT mode 0, this is a new mpt_current_root to expand
                return next

            # if taking any other branch node value than the depth of the node itself, we go 1 nibble deeper,
            # and must not exceed the max depth
            new_depth = last.mpt_lookup_nibble_depth + 1
            assert new_depth <= 32

            # get the top 4 bits, after the lookup so far
            branch_lookup_nibble = (last.mpt_lookup_key << (last.mpt_lookup_nibble_depth*4)) >> (256 - 4)

            # new node to expand into
            next.mpt_current_root = branch_nodes[branch_lookup_nibble]
            next.mpt_lookup_nibble_depth = new_depth
            return next

    return reader_step_gen


def write_start_step(trac: StepsTrace) -> Step:
    last = trac.last()
    next = last.copy()
    if len(last.mpt_value) >= 32:
        next.mpt_current_root = mpt_hash(last.mpt_value)
    else:
        next.mpt_current_root = last.mpt_value
    next.mpt_mode = 3  # continue to writing
    return next


# TODO: init claim with mpt_current_root set to state-root (or account storage root)
def next_mpt_step(trac: StepsTrace) -> Step:
    last = trac.last()
    mpt_mode = last.mpt_mode

    # TODO: define flag to switch between global/account work
    if last.mpt_global:
        trie = trac.world_accounts()
    else:
        trie = trac.account_storage(last.mpt_address_target)

    if mpt_mode == 0:  # returning, back to MPT user
        caller = trac.by_index(next.return_to_step)
        next = caller.copy()
        # remember the value we read
        next.mpt_value = last.mpt_value
        # remember the last node root we touched (top or bottom, depending on read/write)
        next.mpt_current_root = last.mpt_current_root
        return next

    if mpt_mode == 1:  # reading
        proc = make_reader_step_gen(trie)
        return proc(trac)

    if mpt_mode == 2:  # writing start (value to be mapped to node root)
        return write_start_step(trac)

    if mpt_mode == 3:  # writing



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
