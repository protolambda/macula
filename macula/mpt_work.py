from .trace import StepsTrace, Processor, MPT
from .step import *
from enum import IntEnum
from . import keccak_256


# Doesn't decode recursively. Returns a list of element bytes (including their RLP length-prefix etc.)
def rlp_decode_node(data: bytes) -> list:
    if len(data) == 0:  # empty byte strings are used to represent none-existent nodes
        return []
    # generator/verifier just reverts with error if the MPT node data is malformatted
    first_byte = data[0]
    if first_byte < 0xc0:
        # not decoding the bytestring here
        raise Exception("invalid first byte in RLP data: %d" % first_byte)
    data = data[1:]  # strip first byte
    list_length: int  # byte size of total RLP payload, i.e. everything except the prefix length
    if first_byte <= 0xf7:
        list_length = first_byte - 0xc0
    else:
        length_of_length = first_byte - 0xf7
        if len(data) < length_of_length:
            raise Exception("not enough bytes for list length")
        list_length = int.from_bytes(data[:length_of_length], byteorder='big')
        data = data[length_of_length:]

    if list_length != len(data):
        raise Exception("unexpected list length")

    out = []
    while len(data) > 0:
        elem_first_byte = data[0]
        size: int
        if elem_first_byte <= 0x7f:
            size = 1
        elif elem_first_byte <= 0xb7:
            elem_str_length = elem_first_byte - 0x80
            size = 1+elem_str_length
        elif elem_first_byte <= 0xbf:
            elem_length_of_length = elem_first_byte - 0xb7
            elem_str_length = int.from_bytes(data[1:1+elem_length_of_length], byteorder='big')
            size = 1+elem_length_of_length+elem_str_length
        elif elem_first_byte <= 0xf7:
            list_payload_length = elem_first_byte - 0xc0
            size = 1 + list_payload_length
        else:
            elem_length_of_length = elem_first_byte - 0xf7
            list_payload_length = int.from_bytes(data[1:1+elem_length_of_length], byteorder='big')
            size = 1+elem_length_of_length+list_payload_length
        out.append(data[:size])
        data = data[size:]

    if len(out) != 2 and len(out) != 17:
        raise Exception("unexpected amount of elements in list RLP")

    return out


# Strip the length prefix of a RLP string (leaves the bare string) or list (leaves the concatenated RLP payloads).
def rlp_strip_length_prefix(data: bytes) -> bytes:
    elem_first_byte = data[0]
    size: int
    if elem_first_byte <= 0xb7:
        return data[1:]
    elif elem_first_byte <= 0xbf:
        elem_length_of_length = elem_first_byte - 0xb7
        return data[1+elem_length_of_length:]
    elif elem_first_byte <= 0xf7:
        return data[1:]
    else:
        elem_length_of_length = elem_first_byte - 0xb7
        return data[1+elem_length_of_length:]


def int_byte_length(l: int) -> int:
    ll = 1
    while l > 0xff:
        ll += 1
        l >>= 8
    return ll


# Adds the RLP prefix, for strings *only*. NOT RLP-encoded lists.
def rlp_add_str_length_prefix(data: bytes) -> bytes:
    if len(data) == 0:
        return data  # empty string
    if len(data) == 1 and data[0] <= 0x7f:
        return data  # single byte, low enough to be encoded as-is
    if len(data) <= 55:
        return (0x80 + len(data)).to_bytes(length=1, byteorder='big') + data
    else:
        l = len(data)
        ll = int_byte_length(l)  # figure out byte length of the length
        return (0xb7 + ll).to_bytes(length=1, byteorder='big') + l.to_bytes(length=ll, byteorder='big') + data


# takes a list of RLP-encoded elements, concatenates them, and adds the appropriate list-prefix
def rlp_encode_node(items: list) -> bytes:
    if len(items) == 0:
        return b""
    data = b''.join(items)
    if len(data) <= 55:
        return (0xc0 + len(data)).to_bytes(length=1, byteorder='big') + data
    else:
        l = len(data)
        ll = int_byte_length(l)  # figure out byte length of the length
        return (0xbf + ll).to_bytes(length=1, byteorder='big') + l.to_bytes(length=ll, byteorder='big') + data


class MPTTreeSource(IntEnum):
    WORLD_ACCOUNTS = 0x00
    ACCOUNT_STORAGE = 0x01
    # TODO: we could also interface with transactions and receipts once we implement block-fraud-proofs.
    TRANSACTIONS = 0x02
    RECEIPTS = 0x03


class MPTAccessMode(IntEnum):
    # top to bottom tree traversal, get value by key, starting from the given MPT root
    READING = 0x00
    # after reading from top to closest destination, modify the node and bubble up the change
    WRITING = 0x01
    # after reading from top to closest node, remove it, and bubble up the change. Removal may require grafting.
    DELETING = 0x02
    # To graft a sibling node to a parent node (when a branch gets stale on deletion of a node)
    # first step: open the sibling node, get its key path segment (if any), append to grafting path
    GRAFTING_A = 0x03
    # second step: on the parent,
    #  if parent is an extension: rewrite with (extension_prefix ++ grafting_path) as path
    #  if parent is a branch: write the node into place (using extension if len(path) > 0)
    #  (parent cannot be a leaf or empty node)
    # However, the child can be terminating, and determines the mode of the parent if the parent is leaf/extension.
    # Instead of introducing another var, we split mode B.
    GRAFTING_B_terminating_child = 0x04
    GRAFTING_B_continuing_child = 0x05

    # Controls
    STARTING_READ = 0x10
    STARTING_WRITE = 0x11
    STARTING_DELETE = 0x12

    # no ready-read, reading is top-to-bottom and done.
    # Writes/deletes need to read from the top to bottom before starting the actual write/delete,
    # to establish a trusted connected path to the MPT root. When done reading, they are "ready"
    READY_WRITE = 0x21
    READY_DELETE = 0x22

    RETURNING_READ = 0x30
    RETURNING_WRITE = 0x31
    RETURNING_DELETE = 0x32

    # When not performing MPT work, the access is inactive
    INACTIVE = 0xf0
    # After performing MPT work. After reading the value the calling step should reset it back to INACTIVE
    DONE = 0xff



def mpt_hash(data: bytes) -> Bytes32:
    return keccak_256(data)


BLANK_NODE = b""  # TODO: empty node doesn't have special RLP encoding, does it?
BLANK_ROOT = mpt_hash(BLANK_NODE)


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
    path_u256 = uint256(int.from_bytes(encoded_path[1:].ljust(32, b'\x00'), byteorder='big'))
    path_nibble_len = len(encoded_path[1:]) * 2
    assert path_nibble_len <= 64  # = 32 bytes max, or 63 if odd length
    if not evenlen:  # if odd, then the 4 bits "after" (when hex encoded) the flag bits are part of the path
        assert path_nibble_len < 64
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


def rlp_if_bytes32(v: bytes) -> bytes:
    assert len(v) <= 32  # sanity check
    if len(v) == 32:
        return rlp_add_str_length_prefix(v)
    else:
        return v


def mpt_step_with_trie(last: Step, trie: MPT) -> Step:

    def new_2_node(path: bytes, content: bytes, rlp_encode_hash=False):
        # The content must already be RLP encoded (i.e. it's a length prefixed hash or a small RLP structure).
        # The path is not yet RLP encoded.
        rlp_node = rlp_encode_node([rlp_add_str_length_prefix(path), content])
        if len(rlp_node) >= 32:
            trie.put_node(rlp_node)  # can skip this in verification, we don't read the DB after writing.
            out = mpt_hash(rlp_node)
            if rlp_encode_hash:
                return rlp_add_str_length_prefix(out)
            else:
                return out
        else:
            # return as-is, no hashing, as it's already small enough to embed in-place,
            # and distinct because it's shorter than 32 bytes.
            return rlp_node

    def new_branch_node(items: list, rlp_encode_hash=False) -> bytes:
        # The items must already all be RLP encoded
        # (i.e. each is either a length prefixed hash or a small RLP structure).
        rlp_node = rlp_encode_node(items)
        if len(rlp_node) >= 32:
            trie.put_node(rlp_node)  # can skip this in verification, we don't read the DB after writing.
            out = mpt_hash(rlp_node)
            if rlp_encode_hash:
                return rlp_add_str_length_prefix(out)
            else:
                return out
        else:
            # return as-is, no hashing, as it's already small enough to embed in-place,
            # and distinct because it's shorter than 32 bytes.
            return rlp_node

    access = MPTAccessMode(int(last.mpt_work.mode))

    assert access != MPTAccessMode.INACTIVE and access != MPTAccessMode.DONE

    # Note: this MPT code assumes:
    #  - that values in the MPT tree can have keys with different lengths, like the real MPT spec, unlike e.g. account trie.
    #  - supports different key lengths, but only < 32 bytes.

    # Magic:
    #  - when reading, we take the last step node and traverse deeper with the next step.
    #  - when writing, we take the lookup step that created the current step,
    #     and produce a step that bubbles-up changes from the last step.
    #    I.e. writing first does a read from top-to-bottom to learn to trust whatever nodes it's modifying,
    #    then modifies/splits whatever necessary as it bubbles up the change by unwinding.
    # - when deleting, we read the path from top-to-bottom first as pre-requisite, then change to deletion mode,
    #   and delete the targeted node.
    #     - If this leaves a single-node branch, we need to get clean up the connection between the remaining node and the parent
    #       - If the remaining node is the vt node, we can substitute the branch for this node, by bubbling it up as write.
    #       - If the remaining node is in 0...16, then it can go deeper, and we need to construct a graft.
    # - when grafting, we start from the removed branch node.
    #   - We continue deeper to figure out the child-side of the graft path segment (part A)
    #   - And then go back to the parent, to insert the child with its new path.
    #     - If the parent is a leaf/extension kind of node: we connect the paths with its own segment, the new node propagates up as a write.
    #     - If the parent is a branch node: we insert it as an extension/leaf into the branch slot that referenced the old removed branch.

    if access == MPTAccessMode.READING:
        content = last
        next = content.copy()

        # index of last step becomes the parent of the next step
        next.mpt_work.parent_node_step.change(selector=1, value=last)

        if content.mpt_work.lookup_key_nibbles == content.mpt_work.lookup_nibble_depth:  # have we arrived yet?
            if len(content.mpt_work.current_root) < 32:
                value = content.mpt_work.current_root
            else:
                value = trie.get_node(content.mpt_work.current_root)
                if mpt_hash(value) != next.mpt_work.current_root:
                    raise Exception("mpt hash of node value does not match expected hash, bad value witness!")

            # TODO: the returned value may be an RLP-encoded empty byte string if the bottom node
            #  is an empty branch node. Counts as error?

            next.mpt_work.value = value
            # TODO: after reading, the current-root/value is to be read, not to replace the root reference. Needs different mode.
            next.mpt_work.mode = content.mpt_work.mode_on_finish
            return next

    elif access == MPTAccessMode.WRITING:
        # have we bubbled up to the top yet?
        if last.mpt_work.lookup_nibble_depth == 0:
            next = last.copy()
            next.mpt_work.mode = last.mpt_work.mode_on_finish
            return next

        # We follow the same logic-flow as if we were at this step,
        # but instead of going deeper by digging into the node provided by the content,
        # we modify a copy of that node and bubble up the change.
        #
        # we're unwinding back to parent nodes, not on last node.
        content = last.mpt_work.parent_node_step.value()
        next = content.copy()
    elif access == MPTAccessMode.DELETING:
        # have we bubbled up to the top yet?
        if last.mpt_work.lookup_nibble_depth == 0:
            # If we're at the top, we have deleted the last item in the trie.
            # For an empty trie, write an empty node
            next = last.copy()
            next.mpt_work.mode = last.mpt_work.mode_on_finish
            trie.put_node(BLANK_NODE)
            next.mpt_work.current_root = BLANK_ROOT
            return next

        # similar to writing, after reading from top to bottom,
        # we bubble back to delete the necessary nodes
        content = last.mpt_work.parent_node_step.value()
        # no next value yet, we don't now if we're going up or down yet (need to go down if starting a graft)
    elif access == MPTAccessMode.GRAFTING_A:
        # back to the parent after we get the details of the current node to graft with
        content = last.mpt_work.parent_node_step.value()
        assert content is not None
        next = content.copy()
    elif access == MPTAccessMode.GRAFTING_B_terminating_child or access == MPTAccessMode.GRAFTING_B_continuing_child:
        # have we bubbled up to the top yet?
        if last.mpt_work.lookup_nibble_depth == 0:
            # if we're grafting at the top, we make the top a leaf/extension node
            next = last.copy()
            next.mpt_work.mode = last.mpt_work.mode_on_finish
            path_nibble_len = last.mpt_work.graft_key_nibbles

            # can only be 0 if it were a vt node, but we turn those in writes, not grafts.
            assert path_nibble_len > 0

            # top node becomes leaf/extension
            terminating_child = (access == MPTAccessMode.GRAFTING_B_terminating_child)
            path_u256 = last.mpt_work.graft_key_segment
            new_path_encoded = encode_path(path_u256, path_nibble_len, terminating_child)
            new_content = rlp_if_bytes32(last.mpt_work.current_root)
            new_key = new_2_node(new_path_encoded, new_content)
            next.mpt_work.current_root = new_key
            return next

        # bubble up the graft result after modifying the parent end of our graft
        content = last.mpt_work.parent_node_step.value()
        assert content is not None
        next = content.copy()
    else:
        raise NotImplementedError

    data = bytes(content.mpt_work.current_root)
    if len(data) >= 32:  # if not encoded in-place, then need a DB lookup
        # If not arrived yet, then expand it
        key = data
        data = trie.get_node(key)
        # check that the provided MPT node witness data matches the request node root
        if mpt_hash(data) != key:
            raise Exception("mpt hash of rlp node does not match expected hash, bad witness data!")

    # decode into a list of raw byte strings.
    # These strings may be 32-byte hashes, or RLP-encoded data if < 32 bytes
    data_li = rlp_decode_node(data)
    if len(data_li) == 0:
        if access == MPTAccessMode.READING:
            next.mpt_work.current_root = b""
            # stop recursing deeper, null value. (e.g. due to empty branch slot in parent node on our path)
            next.mpt_work.value = BLANK_NODE
            next.mpt_work.fail_lookup = 1
            next.mpt_work.mode = content.mpt_work.mode_on_finish
            return next
        elif access == MPTAccessMode.WRITING:
            # Empty value means we can skip to the next parent, the key didn't exist, or the value is empty.
            # regardless, it will have to be overwritten by modifying the parent.

            target_root = last.mpt_work.current_root
            remaining_depth = content.mpt_work.lookup_key_nibbles - content.mpt_work.lookup_nibble_depth
            # if the write is deeper than this NULL value, then place a leaf with prefix.
            if remaining_depth > 0:
                # shift out the part that we already traversed from the top (if any)
                target_prefix = content.mpt_work.lookup_key << (content.mpt_work.lookup_nibble_depth*4)
                encoded_path = encode_path(target_prefix, remaining_depth, True)
                target_root = new_2_node(encoded_path, rlp_if_bytes32(target_root))

            next.mpt_work.current_root = target_root
            return next
        elif access == MPTAccessMode.DELETING:
            # bubbled up to an already empty node? Then it didn't exist, should never happen.
            raise Exception("deletion should not have been started, the node was not present (empty already)")
        elif access in (MPTAccessMode.GRAFTING_A, MPTAccessMode.GRAFTING_B_terminating_child, MPTAccessMode.GRAFTING_B_continuing_child):
            raise Exception("cannot graft to a NULL parent")
        else:
            raise NotImplementedError

    elif len(data_li) == 2:
        # Path is the first value of the tuple, regardless of extension/leaf type choice.
        # It's RLP encoded, we want the byte string, and then decode it into a nibble path.
        encoded_path = rlp_strip_length_prefix(data_li[0])
        assert len(encoded_path) >= 1
        terminating, path_u256, path_nibble_len = decode_path(encoded_path)

        if access == MPTAccessMode.GRAFTING_A:
            # take path (in-between part of the graft), append the child-side of the grafting,
            # and bubble up with GRAFTING_B_terminating/continuing_child
            prev_segment = last.mpt_work.graft_key_segment
            prev_segment_nibbles = last.mpt_work.graft_key_nibbles
            # append the path of the child we're grafting by shifting it to after the graft segment we have so far
            prev_segment |= path_u256 >> prev_segment_nibbles
            next.mpt_work.graft_key_segment = prev_segment
            next.mpt_work.graft_key_nibbles = prev_segment_nibbles + path_nibble_len
            if terminating:
                next.mpt_work.mode = MPTAccessMode.GRAFTING_B_terminating_child
            else:
                next.mpt_work.mode = MPTAccessMode.GRAFTING_B_continuing_child
            # and don't forget to propagate the contents we're grafting
            # (we're going up, back to parent side of graft)
            next.mpt_work.current_root = last.mpt_work.current_root

            return next
        elif access == MPTAccessMode.GRAFTING_B_terminating_child or access == MPTAccessMode.GRAFTING_B_continuing_child:
            terminating_child = (access == MPTAccessMode.GRAFTING_B_terminating_child)
            # take path, append it to the parent-side of the grafting
            prev_segment = last.mpt_work.graft_key_segment
            prev_segment_nibbles = last.mpt_work.graft_key_nibbles
            # append the grafting work to the parent by shifting it to the end of the parent path
            path_u256 |= prev_segment >> path_nibble_len
            path_nibble_len += prev_segment_nibbles

            # now we have a new grafted path to the child node we are grafting,
            # create the node (a leaf or extension) by bubbling it up as a write.
            new_path_encoded = encode_path(path_u256, path_nibble_len, terminating_child)
            new_content = rlp_if_bytes32(last.mpt_work.current_root)
            new_key = new_2_node(new_path_encoded, new_content)
            next.mpt_work.current_root = new_key
            # switch to writing, we just need to propagate the one change we made, no further grafting/deletion
            next.mpt_work.mode = MPTAccessMode.WRITING

            return next

        key_remainder = content.mpt_work.lookup_key << (content.mpt_work.lookup_nibble_depth*4)
        new_depth = content.mpt_work.lookup_nibble_depth + path_nibble_len

        # check we have read the full key, not more and not less
        if new_depth == content.mpt_work.lookup_key_nibbles:
            # this is a key of equal length, but might not yet be it
            if key_remainder == path_u256:
                # this is at or next to the node we are looking for!

                if access == MPTAccessMode.READING:
                    # it's a leaf, but we'll expand
                    # leaf expand in case it was hashed (>= 32 bytes)
                    # extensions always extend (key can match and point to a branch node that holds the value)
                    if len(data_li[1]) >= 32:
                        # It's a hashed reference, just store the hash instead of the RLP-encoded hash
                        next.mpt_work.current_root = rlp_strip_length_prefix(data_li[1])
                    else:
                        next.mpt_work.current_root = data_li[1]
                    next.mpt_work.lookup_nibble_depth = new_depth
                    # stay in the same MPT mode, this is a new current_root to expand
                    return next
                elif access == MPTAccessMode.WRITING:
                    # overwrite the old node value, and compute the root to bubble up the change
                    new_key = new_2_node(data_li[0], rlp_if_bytes32(last.mpt_work.current_root))
                    next.mpt_work.current_root = new_key

                    # stay in the same MPT mode, this is a new current_root to bubble up
                    return next
                elif access == MPTAccessMode.DELETING:
                    # It must be a leaf we are deleting:
                    # An extension leads to a branch, and a branch has multiple nodes.
                    # We only delete one of those at a time,
                    # so the other gets grafted to the extension before it would get deleted.
                    assert terminating
                    # Bubbling up.
                    assert content is not None
                    next = content.copy()
                    # delete the node altogether,
                    # and bubble up to delete any other nodes that would otherwise reference it as last thing.
                    trie.put_node(BLANK_NODE)
                    next.mpt_work.current_root = BLANK_ROOT
                    return next
                else:
                    raise NotImplementedError
            else:
                # this is just a sibling node with equal key length and common prefix

                if access == MPTAccessMode.READING:
                    next.mpt_work.fail_lookup = 2
                    next.mpt_work.mode = content.mpt_work.mode_on_finish
                    return next
                elif access == MPTAccessMode.WRITING:

                    remainder_nibble_len = content.mpt_work.lookup_key_nibbles - content.mpt_work.lookup_nibble_depth
                    assert remainder_nibble_len == path_nibble_len  # sanity check

                    prefix_path, prefix_len = common_nibble_prefix(
                        key_remainder, path_u256, remainder_nibble_len, path_nibble_len)

                    leaf_sibling = data_li[1]
                    leaf_new = rlp_if_bytes32(last.mpt_work.current_root)

                    # if the values do not differ only in the last nibble, they need their own node
                    if prefix_len + 1 < path_nibble_len:
                        remaining_len = path_nibble_len - prefix_len - 1
                        leaf_sibling_path = encode_path(path_u256 << ((prefix_len+1)*4), remaining_len, True)
                        leaf_new_path = encode_path(key_remainder << ((prefix_len+1)*4), remaining_len, True)

                        leaf_sibling = new_2_node(leaf_sibling_path, leaf_sibling, rlp_encode_hash=True)
                        leaf_new = new_2_node(leaf_new_path, leaf_new, rlp_encode_hash=True)

                    # now split by putting them in a branch
                    branch_node = [b""] * 17
                    branch_node[(path_u256 << (prefix_len*4)) & (0xF << (256-4))] = leaf_sibling
                    branch_node[(key_remainder << (prefix_len*4)) & (0xF << (256-4))] = leaf_new

                    branch_root = new_branch_node(branch_node)

                    # and if they had a common prefix, they need to get extended to
                    if prefix_len > 0:
                        extension_path = encode_path(prefix_path, prefix_len, False)
                        extension_root = new_2_node(extension_path, rlp_if_bytes32(branch_root))
                        next.mpt_work.current_root = extension_root
                    else:
                        next.mpt_work.current_root = branch_root

                    return next
                elif access == MPTAccessMode.DELETING:
                    raise Exception("deletion should not have been started,"
                                    " the node was not present (partially common prefix)")
                else:
                    raise NotImplementedError
        elif new_depth < content.mpt_work.lookup_key_nibbles:
            # the node we are looking for does not exist,
            # but another leaf/extension exists with a shorter key that is a prefix of our key

            if access == MPTAccessMode.READING:
                if terminating:
                    next.mpt_work.fail_lookup = 3
                    next.mpt_work.mode = content.mpt_work.mode_on_finish
                    return next
                else:
                    # extension size is on-track, check if it matches
                    key_remainder = content.mpt_work.lookup_key << (content.mpt_work.lookup_nibble_depth*4)
                    # mask out the part of the key that should match this entry
                    mask = (uint256(1) << (path_nibble_len*4)) - 1
                    shifted_mask = mask << (256 - path_nibble_len*4)
                    key_part = key_remainder & shifted_mask

                    if key_part != path_u256:
                        # extension/leaf leads to some other key, not what we are looking for
                        next.mpt_work.fail_lookup = 6
                        next.mpt_work.mode = content.mpt_work.mode_on_finish
                        return next
                    else:
                        # extension/leaf matches, it's on our path, we can find the node!

                        node = data_li[1]
                        if len(node) >= 32:
                            node = rlp_strip_length_prefix(node)
                        # the value of the extension will be the next hashed node to expand into
                        next.mpt_work.current_root = node

                        next.mpt_work.lookup_nibble_depth = new_depth
                        # stay in the same MPT mode, this is a new current_root to expand
                        return next
            elif access == MPTAccessMode.WRITING:
                remainder_nibble_len = content.mpt_work.lookup_key_nibbles - content.mpt_work.lookup_nibble_depth
                assert path_nibble_len < remainder_nibble_len  # sanity check

                prefix_path, prefix_len = common_nibble_prefix(
                    key_remainder, path_u256, remainder_nibble_len, path_nibble_len)

                target_sibling = data_li[1]
                target_new = rlp_if_bytes32(last.mpt_work.current_root)

                # if there's more than 1 nibble difference,
                # our value needs a leaf/extension node and can't just go into the branch slot
                if path_nibble_len + 1 < remainder_nibble_len:
                    remaining_len = remainder_nibble_len - prefix_len - 1
                    target_new_path = encode_path(key_remainder << ((prefix_len+1)*4), remaining_len, terminating)
                    target_new = new_2_node(target_new_path, target_new, rlp_encode_hash=True)

                # now split by putting them in a branch
                branch_node = [b""] * 17
                branch_node[16] = target_sibling
                branch_node[(key_remainder << (prefix_len*4)) & (0xF << (256-4))] = target_new

                branch_root = new_branch_node(branch_node)

                # and if they had a common prefix, they need to get extended to
                if prefix_len > 0:
                    extension_path = encode_path(prefix_path, prefix_len, False)
                    next.mpt_work.current_root = new_2_node(extension_path, rlp_if_bytes32(branch_root))
                else:
                    next.mpt_work.current_root = branch_root

                return next
            elif access == MPTAccessMode.DELETING:
                raise Exception("deletion should not have been started,"
                                " the node was not present (partially common prefix, shorter key)")
            else:
                raise NotImplementedError

        elif new_depth > content.mpt_work.lookup_key_nibbles:
            # the node we are looking for does not exist,
            # but another leaf/extension exists with a longer key of which our key is a prefix

            if access == MPTAccessMode.READING:
                next.mpt_work.fail_lookup = 4
                next.mpt_work.mode = content.mpt_work.mode_on_finish
                return next
            elif access == MPTAccessMode.WRITING:
                remainder_nibble_len = content.mpt_work.lookup_key_nibbles - content.mpt_work.lookup_nibble_depth
                assert path_nibble_len > remainder_nibble_len  # sanity check

                prefix_path, prefix_len = common_nibble_prefix(
                    key_remainder, path_u256, remainder_nibble_len, path_nibble_len)

                target_sibling = data_li[1]
                target_new = rlp_if_bytes32(last.mpt_work.current_root)

                # if there's more than 1 nibble difference,
                # the other needs a leaf/extension node and can't just go into the branch slot
                if path_nibble_len > remainder_nibble_len + 1:
                    remaining_len = path_nibble_len - prefix_len - 1
                    target_sibling_path = encode_path(path_u256 << ((prefix_len+1)*4), remaining_len, terminating)
                    target_sibling = new_2_node(target_sibling_path, target_sibling)

                # now split by putting them in a branch
                branch_node = [b""] * 17
                branch_node[(path_u256 << (prefix_len*4)) & (0xF << (256-4))] = target_sibling
                branch_node[16] = target_new

                branch_root = new_branch_node(branch_node)

                # and if they had a common prefix, they need to get extended to
                if prefix_len > 0:
                    extension_path = encode_path(prefix_path, prefix_len, False)
                    next.mpt_work.current_root = new_2_node(extension_path, rlp_if_bytes32(branch_root))
                else:
                    next.mpt_work.current_root = branch_root
                return next
            elif access == MPTAccessMode.DELETING:
                raise Exception("deletion should not have been started,"
                                " the node was not present (partially common prefix, longer key)")
            else:
                raise NotImplementedError
    elif len(data_li) == 17:

        if access == MPTAccessMode.GRAFTING_A:
            # if the child is a branch, it has no prefixing path segment,
            # so it can grafted without modifying the graft path.
            # keep the current_root, and bubble back up.
            return next

        if content.mpt_work.lookup_nibble_depth == content.mpt_work.lookup_key_nibbles:
            # we arrived at the key depth already, there are other nodes with longer keys,
            # but we only care about the vt node (17th of branch)

            if access == MPTAccessMode.GRAFTING_B_terminating_child or access == MPTAccessMode.GRAFTING_B_continuing_child:
                raise Exception("invalid MPT: cannot graft child node to branch vt slot, vt is always terminal")
            if access == MPTAccessMode.READING:
                if len(data_li[16]) >= 32:
                    next.mpt_work.current_root = rlp_strip_length_prefix(data_li[16])
                else:
                    next.mpt_work.current_root = data_li[16]
                # stay in the same MPT mode, this is a new current_root to expand
                return next
            elif access == MPTAccessMode.WRITING:
                # we arrived at the key depth already, there are other nodes with longer keys,
                # but we only care about the vt node (17th of branch)
                data_li[16] = rlp_if_bytes32(last.mpt_work.current_root)

                branch_root = new_branch_node(data_li)
                next.mpt_work.current_root = branch_root

                # stay in the same MPT mode, this is a new current_root to bubble up
                return next
            elif access == MPTAccessMode.DELETING:
                # if there is only a single other branch value left, we need to remove the branch,
                # and graft the remaining value to the parent.
                remaining_count = len(node for node in data_li[:16] if node != b"")
                if remaining_count <= 1:
                    if remaining_count == 0:
                        # MPT was invalid, a branch node with only a vt node should not exist
                        raise Exception("invalid MPT")
                    # get the remaining node
                    remaining_index = [node != b"" for node in data_li].index(True)
                    assert remaining_index != 16
                    remaining_node = data_li[remaining_index]
                    if len(remaining_node) >= 32:
                        remaining_node = rlp_strip_length_prefix(remaining_node)

                    # visit the remaining node
                    next.mpt_work.current_root = remaining_node

                    # after first visiting the grafted child,
                    # immediately go to the parent (we removed this intermediate branch)
                    next.mpt_work.parent_node_step.change(selector=1, value=content.mpt_work.parent_node_step.value())

                    next.mpt_work.graft_key_segment = uint256(remaining_index)
                    next.mpt_work.graft_key_nibbles = 1

                    # we need to add the nibble it was located by, and the remaining node may have a deeper path.
                    # so we continue in grafting mode, and visit the child first.
                    next.mpt_work.mode = MPTAccessMode.GRAFTING_A
                else:
                    # Bubbling up.
                    assert content is not None
                    next = content.copy()
                    # more than 1 node remaining in the branch, we can just empty the vt slot
                    # and bubble up the change as a write-operation.
                    data_li[16] = BLANK_NODE
                    branch_root = new_branch_node(data_li)
                    next.mpt_work.current_root = branch_root
                    # the branch stays with remaining children, switch to writing mode
                    next.mpt_work.mode = MPTAccessMode.WRITING
                    return next
            else:
                raise NotImplementedError

        # if taking any other branch node value than the depth of the node itself, we go 1 nibble deeper,
        # and must not exceed the max depth (all keys are 32 bytes or less,
        # e.g. RLP-encoded receipt-trie indices as key)
        new_depth = content.mpt_work.lookup_nibble_depth + 1
        assert new_depth <= 32

        # get the top 4 bits, after the lookup so far
        branch_lookup_nibble = (content.mpt_work.lookup_key << (content.mpt_work.lookup_nibble_depth*4)) >> (256 - 4)

        if access == MPTAccessMode.READING:
            # new node to expand into
            node = data_li[branch_lookup_nibble]
            if len(node) >= 32:
                node = rlp_strip_length_prefix(node)
            next.mpt_work.current_root = node
            next.mpt_work.lookup_nibble_depth = new_depth
            return next
        elif access == MPTAccessMode.WRITING:
            # new node to bubble up into
            data_li[branch_lookup_nibble] = rlp_if_bytes32(last.mpt_work.current_root)

            branch_root = new_branch_node(data_li)
            next.mpt_work.current_root = branch_root

            # stay in the same MPT mode, this is a new current_root to bubble up
            return next
        elif access == MPTAccessMode.GRAFTING_A:
            # A branch node has no leading path,
            # we can just continue to step B of grafting, the graft-path stays the same,
            # and this branch node is grafted to the parent of the branch we omitted.
            next.mpt_work.graft_key_segment = last.mpt_work.graft_key_segment
            next.mpt_work.graft_key_nibbles = last.mpt_work.graft_key_nibbles
            next.mpt_work.mode = MPTAccessMode.GRAFTING_B_continuing_child  # a branch node is never terminating
            return next

        elif access == MPTAccessMode.GRAFTING_B_terminating_child or access == MPTAccessMode.GRAFTING_B_continuing_child:
            # just like writing, except we need a new leaf/extension node to embed the graft path

            # create leaf/extension node
            terminating_child = (access == MPTAccessMode.GRAFTING_B_terminating_child)
            # take path, append it to the parent-side of the grafting
            graft_path = last.mpt_work.graft_key_segment
            graft_path_nibbles = last.mpt_work.graft_key_nibbles
            # can only be 0 if it were a vt node, but we turn those in writes, not grafts.
            assert graft_path_nibbles > 0
            new_path_encoded = encode_path(graft_path, graft_path_nibbles, terminating_child)
            new_content = rlp_if_bytes32(last.mpt_work.current_root)
            new_key = new_2_node(new_path_encoded, new_content)

            # write the new node into the place of the old branch
            data_li[branch_lookup_nibble] = new_key

            # and bubble up the updated branch
            branch_root = new_branch_node(data_li)
            next.mpt_work.current_root = branch_root

            # switch to writing, we just need to propagate the one change we made, no further grafting/deletion
            next.mpt_work.mode = MPTAccessMode.WRITING
            return next
        elif access == MPTAccessMode.DELETING:
            # if we entered a branch node on the path to our node, but didn't reach our node,
            # then finishing a deletion means that we need to remove the branch if there's only one other node left,
            # or propagate changes if more are left.
            data_li[branch_lookup_nibble] = BLANK_NODE
            remaining_count = len(node for node in data_li if node != b"")
            if remaining_count <= 1:
                if remaining_count == 0:
                    # MPT was invalid, a branch node with only a vt node should not exist
                    raise Exception("invalid MPT")
                # There is only a single other branch value left, we need to remove the branch,
                # and graft the remaining value to the parent.

                # Remember the path to insert between the parent node and the remaining leaf node
                remaining_index = [node != b"" for node in data_li].index(True)

                remaining_node = data_li[remaining_index]

                if len(remaining_node) >= 32:
                    remaining_node = rlp_strip_length_prefix(remaining_node)

                if remaining_index == 16:
                    # Nothing to append, we can just put vt in the old spot of the current branch node
                    # So we go upwards.

                    assert content is not None
                    next = content.copy()

                    # write the remaining node
                    next.mpt_work.current_root = remaining_node

                    # Remaining node has no prefix (vt cannot be a leaf/extension node),
                    # So we can just substitute the branch node with the vt node by continuing in writing mode
                    next.mpt_work.mode = MPTAccessMode.WRITING

                    return next
                else:
                    # first need to visit child side of graft, create a new step
                    next = last.copy()

                    # visit the remaining node
                    next.mpt_work.current_root = remaining_node

                    # after first visiting the grafted child,
                    # immediately go to the parent (we removed this intermediate branch)
                    next.mpt_work.parent_node_step.change(selector=1, value=content.mpt_work.parent_node_step.value())

                    next.mpt_work.graft_key_segment = uint256(remaining_index)
                    next.mpt_work.graft_key_nibbles = 1

                    # we need to add the nibble it was located by, and the remaining node may have a deeper path.
                    # so we continue in grafting mode, and visit the child first.
                    next.mpt_work.mode = MPTAccessMode.GRAFTING_A

                    return next
            else:
                # Bubbling up.
                assert content is not None
                next = content.copy()

                # more than 1 node remaining in the branch, we can just empty our slot
                # and bubble up the change as a write-operation.
                data_li[branch_lookup_nibble] = BLANK_NODE
                branch_root = new_branch_node(data_li)
                next.mpt_work.current_root = branch_root
                # the branch stays with remaining children, switch to writing mode
                next.mpt_work.mode = MPTAccessMode.WRITING
                return next
        else:
            raise NotImplementedError


# TODO: init claim with current_root set to state-root (or account storage root)
def mpt_work_proc(trac: StepsTrace) -> Step:
    last = trac.last()
    mpt_mode = MPTAccessMode(last.mpt_work.mode)

    trie_src = MPTTreeSource(last.mpt_work.tree_source)
    if trie_src == MPTTreeSource.WORLD_ACCOUNTS:
        trie = trac.world_accounts()
    elif trie_src == MPTTreeSource.ACCOUNT_STORAGE:
        addr = Address.from_b32(last.mpt_work.start_reference)
        trie = trac.account_storage(addr)
    else:
        # TODO: support transactions and receipts
        raise NotImplementedError

    if mpt_mode <= 5:  # all internal tree operation modes
        return mpt_step_with_trie(last, trie)

    if mpt_mode == MPTAccessMode.STARTING_READ:
        next = last.copy()
        # TODO: maybe assert we set the read arguments correctly?
        next.mpt_work.mode = MPTAccessMode.READING
        next.mpt_work.mode_on_finish = MPTAccessMode.RETURNING_READ
        return next

    if mpt_mode == MPTAccessMode.STARTING_WRITE:  # writing start (value to be mapped to node root)
        next = last.copy()
        if len(last.mpt_work.value) >= 32:
            next.mpt_work.write_root = mpt_hash(last.mpt_work.value)
        else:
            next.mpt_work.write_root = last.mpt_work.value
        next.mpt_work.mode = MPTAccessMode.READING  # continue to preparation reading
        next.mpt_work.mode_on_finish = MPTAccessMode.READY_WRITE  # return to writer value injection
        return next

    if mpt_mode == MPTAccessMode.STARTING_DELETE:
        next = last.copy()
        # TODO: maybe assert we set the deletion arguments correctly?
        next.mpt_work.mode = MPTAccessMode.READING  # continue to preparation reading
        next.mpt_work.mode_on_finish = MPTAccessMode.READY_DELETE  # return to deletion pivot
        return next

    if mpt_mode == MPTAccessMode.READY_WRITE:
        # once done with reading, the mpt_write_root is injected to do the write.
        next = last.copy()

        # TODO: handle read fail

        next.mpt_work.current_root = last.mpt_work.write_root
        next.mpt_work.mode = MPTAccessMode.WRITING  # continue to writing
        next.mpt_work.mode_on_finish = MPTAccessMode.RETURNING_WRITE  # once done bubbling up, return
        return next

    if mpt_mode == MPTAccessMode.READY_DELETE:
        # once done with reading, the deleting can start
        next = last.copy()

        # TODO: handle read fail

        next.mpt_work.mode = MPTAccessMode.DELETING  # continue to deleting
        next.mpt_work.mode_on_finish = MPTAccessMode.RETURNING_DELETE  # once done bubbling up, return
        return next

    if mpt_mode == MPTAccessMode.RETURNING_READ:  # returning, back to MPT user
        caller = last.return_to_step.value()
        assert caller is not None
        next = caller.copy()
        # TODO: handle read fail
        # remember the value we read
        next.mpt_work.value = last.mpt_work.value
        # and that we returned
        next.mpt_work.mode = MPTAccessMode.DONE
        return next

    if mpt_mode == MPTAccessMode.RETURNING_WRITE:
        caller = last.return_to_step.value()
        assert caller is not None
        next = caller.copy()
        # remember the new MPT root (or any root in the path, if write failed)
        # TODO: handle write fail
        next.mpt_work.current_root = last.mpt_work.current_root
        # and that we are done
        next.mpt_work.mode = MPTAccessMode.DONE
        return next

    if mpt_mode == MPTAccessMode.RETURNING_DELETE:
        caller = last.return_to_step.value()
        assert caller is not None
        next = caller.copy()
        # remember the new MPT root (or any root in the path, if deletion failed)
        # TODO: handle delete fail
        next.mpt_work.current_root = last.mpt_work.current_root
        # and that we are done
        next.mpt_work.mode = MPTAccessMode.DONE
        return next

    raise Exception("unexpected MPT mode: %d" % mpt_mode)

