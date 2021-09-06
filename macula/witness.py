from typing import Dict, List, TypedDict


class StepWitnessData(TypedDict):
    root: str
    # Code is referenced by keccak256 hash in the account value, thus needs a witness.
    # 32 bytes -> bytes  (key and values are 0x prefixed + hex encoded)
    code_by_hash: Dict[str, str]
    # MPT trees (world, account storage, etc.)
    # We mix all MPTs together, since the lookups are all by hash anyway
    # 32 bytes -> bytes  (key and values are 0x prefixed + hex encoded)
    mpt_node_by_hash: Dict[str, str]
    # Partial binary tree, matching the SSZ merkle tree.
    # Instead of a nested structure it's a map of encoded generalized index to corresponding tree node.
    # Each gindex (key) is encodes as big-endian hex string with 0x prefix.
    # Each root (value) is 0x prefixed + hex encoded
    contents: Dict[str, str]


class StepAccessList(TypedDict):
    root: str
    # each gindex is encodes as big-endian hex string with 0x prefix
    accessed_gindices: List[str]
    # list of mpt node hashes (not tree keys), for world and storage all combined
    accessed_world_mpt_nodes: List[str]
    # Code-hashes that were accessed
    accessed_code_hashes: List[str]


# This is JSON object that the fraud-proof generator outputs.
# It represents all witness data of the trace, in a compressed form.
# To get the witness of a single step, use get_step_witness.
class TraceWitnessData(TypedDict):
    # dict: hash -> code  (key and values are 0x prefixed + hex encoded)
    code_by_hash: Dict[str, str]
    # dict: hash -> code  (key and values are 0x prefixed + hex encoded)
    mpt_node_by_hash: Dict[str, str]
    # Covers all the step data, db of parent root -> [left root, right root]
    # All roots are 0x prefixed + hex encoded
    binary_nodes: Dict[str, list]
    # root node reference of each step (0x prefixed + hex encoded)
    steps: List[StepAccessList]

    def get_step_witness(self, i: int) -> StepWitnessData:
        step_acc_li = self.steps[i]

        root = step_acc_li['root']
        code_by_hash = {h: self.code_by_hash[h] for h in step_acc_li['accessed_code_hashes']}
        mpt_node_by_hash = {h: self.mpt_node_by_hash[h] for h in step_acc_li['accessed_world_mpt_nodes']}

        bin_db = self.binary_nodes

        def retrieve_node_by_gindex(i: int, root: str) -> str:
            if i == 1:
                return root

            pivot = 1 << (i.bit_length() - 1)
            go_right = i & pivot != 0
            # mask out the top bit, and set the new top bit
            child = (i | pivot) - (pivot << 1)
            left, right = bin_db[root]
            if go_right:
                return retrieve_node_by_gindex(child, right)
            else:
                return retrieve_node_by_gindex(child, left)

        contents = {g: retrieve_node_by_gindex(int.from_bytes(bytes.fromhex(g[2:]), byteorder='big'), root)
                    for g in step_acc_li['accessed_gindices']}

        return StepWitnessData(
            root=root,
            code_by_hash=code_by_hash,
            mpt_node_by_hash=mpt_node_by_hash,
            contents=contents,
        )
