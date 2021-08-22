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


def encode_path(path: uint256, path_len: int, terminating: bool) -> bytes:
    first_byte = 0
    if path_len % 2 == 1:  # check if odd length
        first_byte |= (0b0001 << 4) | (int(path) & 0xf)
        path <<= 4
        path_len -= 1
    if terminating:  # check if terminating leaf
        first_byte |= 0b0010 << 4
    path = first_byte.to_bytes(length=1, byteorder='big')
    if path_len == 0:
        return path
    remaining_bytes = (int(path) >> (256 - (path_len*4))).to_bytes(length=path_len//2, byteorder='big')
    return path + remaining_bytes


# Takes two paths, and the length of the paths, and outputs the common part and the length of said common part.
# Lengths are in number of nibbles
def common_nibble_prefix(a: uint256, b: uint256, a_len: int, b_len: int) -> (uint256, int):
    prefix = uint256(0)
    max_common = min(a_len, b_len)
    for i in range(max_common):
        a_nib = (a >> (256 - 4)) & 0xF
        b_nib = (b >> (256 - 4)) & 0xF
        if a_nib != b_nib:
            return prefix, i
        prefix = (prefix >> 4) | (a & (0xF << (256 - 4)))
    return prefix, max_common


from enum import Enum
class MPTAccessMode(Enum):
    READING = 0
    WRITING = 1
    DELETING = 2  # TODO


def make_reader_step_gen(trie: MPT, access: MPTAccessMode) -> Processor:
    def reader_step_gen(trac: StepsTrace) -> Step:
        last = trac.last()

        # Magic:
        #  - when reading, we take the last step node and traverse deeper with the next step.
        #  - when writing, we take lookup step that created the current step,
        #     and produce a step that bubbles-up changes from the last step.
        #    I.e. writing first does a read from top-to-bottom to learn to trust whatever nodes it's modifying,
        #    then modifies/splits whatever necessary as it bubbles up the change by unwinding.

        if access == MPTAccessMode.READING:
            content = last
            next = content.copy()

            # index of last step becomes the parent of the next step
            next.mpt_parent_node_step = trac.length() - 1

            if content.mpt_lookup_key_nibbles == content.mpt_lookup_nibble_depth:  # have we arrived yet?
                if len(content.mpt_current_root) < 32:
                    value = content.mpt_current_root
                else:
                    value = trie.get_node(content.mpt_current_root)
                    assert mpt_hash(value) == next.mpt_current_root

                if value == b"":
                    # if we got a branch at the very last key depth,
                    # then we may end with an empty node at branch slot,
                    # this is not technically an error w.r.t. MPT, but shouldn't pass as OK.
                    next.mpt_fail_lookup = 10

                next.mpt_value = value
                next.mpt_mode = content.mpt_mode_on_finish
                return next

        elif access == MPTAccessMode.WRITING:
            # have we bubbled up to the top yet?
            if last.mpt_lookup_nibble_depth == 0:
                next = last.copy()
                next.mpt_mode = last.mpt_mode_on_finish
                return next

            # We follow the same logic-flow as if we were at this step,
            # but instead of going deeper by digging into the node provided by the content,
            # we modify a copy of that node and bubble up the change.
            #
            # we're unwinding back to parent nodes, not on last node.
            content = trac.by_index(last.mpt_parent_node_step)
            next = content.copy()
        else:
            raise NotImplementedError

        # If not arrived yet, then expand it
        data = trie.get_node(content.mpt_current_root)
        # check that the provided MPT node witness data matches the request node root
        assert mpt_hash(data) == content.mpt_current_root

        data_li = rlp_decode_list(data)
        if len(data_li) == 0:
            if access == MPTAccessMode.READING:
                next.mpt_current_root = Bytes32()
                # stop recursing deeper, null value. (e.g. due to empty branch slot in parent node on our path)
                next.mpt_value = b""
                next.mpt_fail_lookup = 1
                next.mpt_mode = content.mpt_mode_on_finish
                return next
            elif access == MPTAccessMode.WRITING:
                # Empty value means we can skip to the next parent, the key didn't exist, or the value is empty.
                # regardless, it will have to be overwritten by modifying the parent.

                # TODO: create leaf node if lookup is deeper

                next.mpt_current_root = last.mpt_current_root
                return next
            else:
                raise NotImplementedError

        elif len(data_li) == 2:
            encoded_path = data_li[0]  # path is the first value of the tuple, regardless of extension/leaf type choice
            assert len(encoded_path) >= 1
            terminating, path_u256, path_nibble_len = decode_path(encoded_path)

            key_remainder = content.mpt_lookup_key << (content.mpt_lookup_nibble_depth*4)
            new_depth = content.mpt_lookup_nibble_depth + path_nibble_len

            # check we have read the full key, not more and not less
            if new_depth == content.mpt_lookup_key_nibbles:
                # this is a key of equal length, but might not yet be it
                if key_remainder == path_u256:
                    # this is at or next to the node we are looking for!

                    if access == MPTAccessMode.READING:
                        # it's a leaf, but we'll expand
                        # leaf expand in case it was hashed (>= 32 bytes)
                        # extensions always extend (key can match and point to a branch node that holds the value)
                        next.mpt_current_root = data_li[1]
                        next.mpt_lookup_nibble_depth = new_depth
                        # stay in the same MPT mode, this is a new mpt_current_root to expand
                        return next
                    elif access == MPTAccessMode.WRITING:
                        # overwrite the old node value, and compute the root to bubble up the change
                        data_li[1] = last.mpt_current_root
                        new_node_raw = rlp_encode_list(data_li)
                        new_key = mpt_hash(new_node_raw)
                        next.mpt_current_root = new_key

                        # keep the trie storage up to date with out changes
                        trie.put_node(new_node_raw)

                        # stay in the same MPT mode, this is a new mpt_current_root to bubble up
                        return next
                    else:
                        raise NotImplementedError
                else:
                    # this is just a sibling node with equal key length and common prefix

                    if access == MPTAccessMode.READING:
                        next.mpt_fail_lookup = 2
                        next.mpt_mode = content.mpt_mode_on_finish
                        return next
                    elif access == MPTAccessMode.WRITING:

                        remainder_nibble_len = content.mpt_lookup_key_nibbles - content.mpt_lookup_nibble_depth
                        assert remainder_nibble_len == path_nibble_len  # sanity check

                        prefix_path, prefix_len = common_nibble_prefix(
                            key_remainder, path_u256, remainder_nibble_len, path_nibble_len)

                        leaf_sibling = data_li[1]
                        leaf_new = last.mpt_current_root

                        # if the values do not differ only in the last nibble, they need their own node
                        if prefix_len + 1 < path_nibble_len:
                            remaining_len = path_nibble_len - prefix_len - 1
                            leaf_sibling_path = encode_path(path_u256 << ((prefix_len+1)*4), remaining_len, True)
                            leaf_new_path = encode_path(key_remainder << ((prefix_len+1)*4), remaining_len, True)

                            leaf_sibling_node = [leaf_sibling_path, leaf_sibling]
                            leaf_new_node = [leaf_new_path, leaf_new]

                            leaf_sibling_raw = rlp_encode_list(leaf_sibling_node)
                            trie.put_node(leaf_sibling_raw)
                            leaf_sibling = mpt_hash(leaf_sibling_raw)

                            leaf_new_raw = rlp_encode_list(leaf_new_node)
                            trie.put_node(leaf_new_raw)
                            leaf_new = mpt_hash(leaf_new_raw)

                        # now split by putting them in a branch
                        branch_node = [b""] * 17
                        branch_node[(path_u256 << (prefix_len*4)) & (0xF << (256-4))] = leaf_sibling
                        branch_node[(key_remainder << (prefix_len*4)) & (0xF << (256-4))] = leaf_new

                        branch_raw = rlp_encode_list(branch_node)
                        trie.put_node(branch_raw)
                        branch_root = mpt_hash(branch_raw)

                        # and if they had a common prefix, they need to get extended to
                        if prefix_len > 0:
                            extension_path = encode_path(prefix_path, prefix_len, False)
                            extension_node = [extension_path, branch_root]

                            extension_raw = rlp_encode_list(extension_node)
                            trie.put_node(extension_raw)
                            extension_root = mpt_hash(extension_raw)
                            next.mpt_current_root = extension_root
                        else:
                            next.mpt_current_root = branch_root

                        return next
                    else:
                        raise NotImplementedError
            elif new_depth < content.mpt_lookup_key_nibbles:
                # the node we are looking for does not exist,
                # but another leaf exists with a shorter key that is a prefix of our key

                if access == MPTAccessMode.READING:
                    if terminating:
                        next.mpt_fail_lookup = 3
                        next.mpt_mode = content.mpt_mode_on_finish
                        return next
                    else:
                        # extension size is on-track, check if it matches
                        key_remainder = content.mpt_lookup_key << (content.mpt_lookup_nibble_depth*4)
                        # mask out the part of the key that should match this entry
                        mask = (uint256(1) << (path_nibble_len*4)) - 1
                        shifted_mask = mask << (256 - path_nibble_len*4)
                        key_part = key_remainder & shifted_mask

                        if key_part != path_u256:
                            # extension leads to some other key, not what we are looking for
                            next.mpt_fail_lookup = 6
                            next.mpt_mode = content.mpt_mode_on_finish
                            return next
                        else:
                            # extension matches, it's on our path, we can find the node!

                            # the value of the extension will be the next hashed node to expand into
                            next.mpt_current_root = data_li[1]

                            next.mpt_lookup_nibble_depth = new_depth
                            # stay in the same MPT mode, this is a new mpt_current_root to expand
                            return next
                elif access == MPTAccessMode.WRITING:
                    remainder_nibble_len = content.mpt_lookup_key_nibbles - content.mpt_lookup_nibble_depth
                    assert path_nibble_len < remainder_nibble_len  # sanity check

                    prefix_path, prefix_len = common_nibble_prefix(
                        key_remainder, path_u256, remainder_nibble_len, path_nibble_len)

                    target_sibling = data_li[1]
                    target_new = last.mpt_current_root

                    # if there's more than 1 nibble difference,
                    # our value needs a leaf/extension node and can't just go into the branch slot
                    if path_nibble_len + 1 < remainder_nibble_len:
                        remaining_len = remainder_nibble_len - prefix_len - 1
                        target_new_path = encode_path(key_remainder << ((prefix_len+1)*4), remaining_len, terminating)
                        target_new_node = [target_new_path, target_new]

                        target_new_raw = rlp_encode_list(target_new_node)
                        trie.put_node(target_new_raw)
                        target_new = mpt_hash(target_new_raw)

                    # now split by putting them in a branch
                    branch_node = [b""] * 17
                    branch_node[16] = target_sibling
                    branch_node[(key_remainder << (prefix_len*4)) & (0xF << (256-4))] = target_new

                    branch_raw = rlp_encode_list(branch_node)
                    trie.put_node(branch_raw)
                    branch_root = mpt_hash(branch_raw)

                    # and if they had a common prefix, they need to get extended to
                    if prefix_len > 0:
                        extension_path = encode_path(prefix_path, prefix_len, False)
                        extension_node = [extension_path, branch_root]

                        extension_raw = rlp_encode_list(extension_node)
                        trie.put_node(extension_raw)
                        extension_root = mpt_hash(extension_raw)
                        next.mpt_current_root = extension_root
                    else:
                        next.mpt_current_root = branch_root

                    return next
                else:
                    raise NotImplementedError

            elif new_depth > content.mpt_lookup_key_nibbles:
                # the node we are looking for does not exist,
                # but another leaf/extension exists with a longer key of which our key is a prefix

                if access == MPTAccessMode.READING:
                    next.mpt_fail_lookup = 4
                    next.mpt_mode = content.mpt_mode_on_finish
                    return next
                elif access == MPTAccessMode.WRITING:
                    remainder_nibble_len = content.mpt_lookup_key_nibbles - content.mpt_lookup_nibble_depth
                    assert path_nibble_len > remainder_nibble_len  # sanity check

                    prefix_path, prefix_len = common_nibble_prefix(
                        key_remainder, path_u256, remainder_nibble_len, path_nibble_len)

                    target_sibling = data_li[1]
                    target_new = last.mpt_current_root

                    # if there's more than 1 nibble difference,
                    # the other needs a leaf/extension node and can't just go into the branch slot
                    if path_nibble_len > remainder_nibble_len + 1:
                        remaining_len = path_nibble_len - prefix_len - 1
                        target_sibling_path = encode_path(path_u256 << ((prefix_len+1)*4), remaining_len, terminating)
                        target_sibling_node = [target_sibling_path, target_sibling]

                        target_sibling_raw = rlp_encode_list(target_sibling_node)
                        trie.put_node(target_sibling_raw)
                        target_sibling = mpt_hash(target_sibling_raw)

                    # now split by putting them in a branch
                    branch_node = [b""] * 17
                    branch_node[(path_u256 << (prefix_len*4)) & (0xF << (256-4))] = target_sibling
                    branch_node[16] = target_new

                    branch_raw = rlp_encode_list(branch_node)
                    trie.put_node(branch_raw)
                    branch_root = mpt_hash(branch_raw)

                    # and if they had a common prefix, they need to get extended to
                    if prefix_len > 0:
                        extension_path = encode_path(prefix_path, prefix_len, False)
                        extension_node = [extension_path, branch_root]

                        extension_raw = rlp_encode_list(extension_node)
                        trie.put_node(extension_raw)
                        extension_root = mpt_hash(extension_raw)
                        next.mpt_current_root = extension_root
                    else:
                        next.mpt_current_root = branch_root

                    return next

                else:
                    raise NotImplementedError
        elif len(data_li) == 17:

            if content.mpt_lookup_nibble_depth == content.mpt_lookup_key_nibbles:
                # we arrived at the key depth already, there are other nodes with longer keys,
                # but we only care about the vt node (17th of branch)

                if access == MPTAccessMode.READING:
                    next.mpt_current_root = data_li[16]
                    # stay in the same MPT mode, this is a new mpt_current_root to expand
                    return next
                elif access == MPTAccessMode.WRITING:
                    # we arrived at the key depth already, there are other nodes with longer keys,
                    # but we only care about the vt node (17th of branch)
                    data_li[16] = last.mpt_current_root

                    branch_raw = rlp_encode_list(data_li)
                    trie.put_node(branch_raw)
                    branch_root = mpt_hash(branch_raw)
                    next.mpt_current_root = branch_root

                    # stay in the same MPT mode, this is a new mpt_current_root to bubble up
                    return next
                else:
                    raise NotImplementedError

            # if taking any other branch node value than the depth of the node itself, we go 1 nibble deeper,
            # and must not exceed the max depth (all keys are 32 bytes or less,
            # e.g. RLP-encoded receipt-trie indices as key)
            new_depth = content.mpt_lookup_nibble_depth + 1
            assert new_depth <= 32

            # get the top 4 bits, after the lookup so far
            branch_lookup_nibble = (content.mpt_lookup_key << (content.mpt_lookup_nibble_depth*4)) >> (256 - 4)

            if access == MPTAccessMode.READING:
                # new node to expand into
                next.mpt_current_root = data_li[branch_lookup_nibble]
                next.mpt_lookup_nibble_depth = new_depth
                return next
            elif access == MPTAccessMode.WRITING:
                # new node to bubble up into
                data_li[branch_lookup_nibble] = last.mpt_current_root

                branch_raw = rlp_encode_list(parent_data_li)
                trie.put_node(branch_raw)
                branch_root = mpt_hash(branch_raw)
                next.mpt_current_root = branch_root

                # stay in the same MPT mode, this is a new mpt_current_root to bubble up
                return next
            else:
                raise NotImplementedError

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
        caller = trac.by_index(last.return_to_step)
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
