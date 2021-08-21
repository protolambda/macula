from .trace import StepsTrace, Processor, MPT
from .step import *


def rlp_decode_list(data: bytes) -> list:
    return []  # TODO


def rlp_encode_list(items: list) -> bytes:
    return b""  # TODO


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

        # index of last step becomes the parent of the next step
        next.mpt_parent_node_step = trac.length() - 1

        if last.mpt_lookup_key_nibbles == last.mpt_lookup_nibble_depth:  # have we arrived yet?
            if len(last.mpt_current_root) < 32:
                value = last.mpt_current_root
            else:
                value = trie.get_node(last.mpt_current_root)
                assert mpt_hash(value) == next.mpt_current_root

            if value == b"":
                # if we got a branch at the very last key depth,
                # then we may end with an empty node at branch slot,
                # this is not technically an error w.r.t. MPT, but shouldn't pass as OK.
                next.mpt_fail_lookup = 10

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
            # stop recursing deeper, null value. (e.g. due to empty branch slot in parent node on our path)
            next.mpt_value = b""
            next.mpt_fail_lookup = 1
            next.mpt_mode = last.mpt_mode_on_finish
            return next

        elif len(data_li) == 2:
            encoded_path = data_li[0]  # path is the first value of the tuple, regardless of extension/leaf type choice
            assert len(encoded_path) >= 1
            terminating, path_u256, path_nibble_len = decode_path(encoded_path)

            if terminating:  # handle leaf
                key_remainder = last.mpt_lookup_key << (last.mpt_lookup_nibble_depth*4)
                new_depth = last.mpt_lookup_nibble_depth + path_nibble_len

                # check we have read the full key, not more and not less
                if new_depth == last.mpt_lookup_key_nibbles:
                    # this is a key of equal length, but might not yet be it
                    if key_remainder == path_u256:
                        # this is the node we are looking for!

                        # it's a leaf, but we'll expand it if it was hashed (>= 32 bytes)
                        next.mpt_current_root = data_li[1]
                        next.mpt_lookup_nibble_depth = new_depth
                        # stay in MPT mode 0, this is a new mpt_current_root to expand
                        return next
                    else:
                        # this is just a sibling node with equal key length and common prefix
                        next.mpt_fail_lookup = 2
                        next.mpt_mode = last.mpt_mode_on_finish
                        return next
                elif new_depth < last.mpt_lookup_key_nibbles:
                    # the node we are looking for does not exist,
                    # but another leaf exists with a shorter key that is a prefix of our key
                    next.mpt_fail_lookup = 3
                    next.mpt_mode = last.mpt_mode_on_finish
                    return next
                elif new_depth > last.mpt_lookup_key_nibbles:
                    # the node we are looking for does not exist,
                    # but another leaf exists with a longer key of which our key is a prefix
                    next.mpt_fail_lookup = 4
                    next.mpt_mode = last.mpt_mode_on_finish
                    return next

            else:  # handle extension

                new_depth = last.mpt_lookup_nibble_depth + path_nibble_len
                # full key may be read if we extend to a branch node
                # that has other longer keys and ours in the special 17th slot
                if new_depth >= last.mpt_lookup_key_nibbles:
                    # extension too long, cannot find the node
                    next.mpt_fail_lookup = 5
                    next.mpt_mode = last.mpt_mode_on_finish
                    return next
                else:
                    # extension size is on-track, check if it matches
                    key_remainder = last.mpt_lookup_key << (last.mpt_lookup_nibble_depth*4)
                    # mask out the part of the key that should match this entry
                    mask = (uint256(1) << (path_nibble_len*4)) - 1
                    shifted_mask = mask << (256 - path_nibble_len*4)
                    key_part = key_remainder & shifted_mask

                    if key_part != path_u256:
                        # extension leads to some other key, not what we are looking for
                        next.mpt_fail_lookup = 6
                        next.mpt_mode = last.mpt_mode_on_finish
                        return next
                    else:
                        # extension matches, it's on our path, we can find the node!

                        # the value of the extension will be the next hashed node to expand into
                        next.mpt_current_root = data_li[1]

                next.mpt_lookup_nibble_depth = new_depth
                # stay in MPT mode 0, this is a new mpt_current_root to expand
                return next

        elif len(data_li) == 17:

            if last.mpt_lookup_nibble_depth == last.mpt_lookup_key_nibbles:
                # we arrived at the key depth already, there are other nodes with longer keys,
                # but we only care about the vt node (17th of branch)
                next.mpt_current_root = data_li[16]
                # stay in MPT mode 0, this is a new mpt_current_root to expand
                return next

            # if taking any other branch node value than the depth of the node itself, we go 1 nibble deeper,
            # and must not exceed the max depth (all keys are 32 bytes or less,
            # e.g. RLP-encoded receipt-trie indices as key)
            new_depth = last.mpt_lookup_nibble_depth + 1
            assert new_depth <= 32

            # get the top 4 bits, after the lookup so far
            branch_lookup_nibble = (last.mpt_lookup_key << (last.mpt_lookup_nibble_depth*4)) >> (256 - 4)

            # new node to expand into
            next.mpt_current_root = data_li[branch_lookup_nibble]
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


def make_writer_step_gen(trie: MPT) -> Processor:
    def write_step(trac: StepsTrace) -> Step:
        last = trac.last()
        parent = trac.by_index(last.mpt_parent_node_step)
        # we're unwinding back to parent nodes, not on last node.
        next = parent.copy()

        # do the reverse as in the read-steps,
        #  but update the node before traversing back up to the root of the trie.

        parent_data = trie.get_node(parent.mpt_current_root)
        # check that the provided MPT node witness data matches the request node root
        assert mpt_hash(parent_data) == parent.mpt_current_root

        parent_data_li = rlp_decode_list(parent_data)
        if len(parent_data_li) != 0:
            # Empty value means we can skip to the next parent, the key didn't exist, or the value is empty.
            # regardless, it will have to be overwritten by modifying the parent.
            next.mpt_write_root = last.mpt_write_root
            return next

        elif len(parent_data_li) == 2:
            encoded_path = parent_data_li[0]  # path is the first value of the tuple, regardless of extension/leaf type choice
            assert len(encoded_path) >= 1
            terminating, path_u256, path_nibble_len = decode_path(encoded_path)

            if terminating:  # handle leaf
                key_remainder = parent.mpt_lookup_key << (parent.mpt_lookup_nibble_depth*4)
                new_depth = parent.mpt_lookup_nibble_depth + path_nibble_len

                # check we have read the full key, not more and not less
                if new_depth == parent.mpt_lookup_key_nibbles:
                    # this is a key of equal length, but might not yet be it
                    if key_remainder == path_u256:
                        # this is the node we are looking for!

                        # overwrite the old node value, anc compute the root to bubble up the change
                        parent_data_li[1] = last.mpt_write_root
                        new_node_raw = rlp_encode_list(parent_data_li)
                        new_key = mpt_hash(new_node_raw)
                        next.mpt_write_root = new_key

                        # keep the trie storage up to date with out changes
                        trie.put_node(new_key, new_node_raw)

                        # stay in MPT mode 0, this is a new mpt_write_root to bubble up
                        return next
                    else:
                        # this is just a sibling node with equal key length and common prefix
                        # TODO: create extension + branch node with single sibling + leaf x 2
                        return next
                elif new_depth < parent.mpt_lookup_key_nibbles:
                    # the node we are looking for does not exist,
                    # but another leaf exists with a shorter key that is a prefix of our key
                    # TODO: create extension + branch node with vt + leaf
                    return next
                elif new_depth > parent.mpt_lookup_key_nibbles:
                    # the node we are looking for does not exist,
                    # but another leaf exists with a longer key of which our key is a prefix
                    # TODO: create extension + branch node with vt + leaf
                    return next

            else:  # handle extension

                new_depth = parent.mpt_lookup_nibble_depth + path_nibble_len
                # full key may be read if we extend to a branch node
                # that has other longer keys and ours in the special 17th slot
                if new_depth >= parent.mpt_lookup_key_nibbles:
                    # extension too long, cannot find the node
                    # TODO: shorten extension, put branch node, continue extension
                    return next
                else:
                    # extension size is on-track, check if it matches
                    key_remainder = parent.mpt_lookup_key << (parent.mpt_lookup_nibble_depth*4)
                    # mask out the part of the key that should match this entry
                    mask = (uint256(1) << (path_nibble_len*4)) - 1
                    shifted_mask = mask << (256 - path_nibble_len*4)
                    key_part = key_remainder & shifted_mask

                    if key_part != path_u256:
                        # extension leads to some other key, not what we are looking for
                        # TODO shorten extension, put branch node, continue two extensions
                        return next
                    else:
                        # extension matches, it's on our path, we can reuse it

                        # the value of the extension will be the next hashed node to expand into
                        parent_data_li[1] = last.mpt_write_root
                        # TODO bubble up

                # stay in MPT mode 0, this is a new mpt_write_root to bubble up
                return next

        elif len(parent_data_li) == 17:

            if parent.mpt_lookup_nibble_depth == parent.mpt_lookup_key_nibbles:
                # we arrived at the key depth already, there are other nodes with longer keys,
                # but we only care about the vt node (17th of branch)
                parent_data_li[16] = last.mpt_write_root
                # TODO bubble up
                # stay in MPT mode 0, this is a new mpt_write_root to expand
                return next

            # if taking any other branch node value than the depth of the node itself, we go 1 nibble deeper,
            # and must not exceed the max depth (all keys are 32 bytes or less,
            # e.g. RLP-encoded receipt-trie indices as key)
            new_depth = parent.mpt_lookup_nibble_depth + 1
            assert new_depth <= 32

            # get the top 4 bits, after the lookup so far
            branch_lookup_nibble = (parent.mpt_lookup_key << (parent.mpt_lookup_nibble_depth*4)) >> (256 - 4)

            # new node to bubble up into
            parent_data_li[branch_lookup_nibble] = last.mpt_write_root
            # TODO bubble up
            return next

    return write_step


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
