import click
from typing import List
from .exec_mode import ExecMode, exec_is_done
from .step import Step, Address, Bytes32
from .capture import CaptureTrace, ExternalSource
from .interpreter import next_step
from .witness import TraceWitnessData, StepAccessList
from remerkleable.tree import PairNode
import json


@click.group()
def cli():
    """Macula - optimistic rollup tech for ethereum
    Contribute here: https://github.com/protolambda/macula
    """


class HttpSource(ExternalSource):
    # TODO: http client
    def get_acc_storage_node(self, addr: Address, key: Bytes32) -> bytes:
        ...
    def get_world_node(self, key: Bytes32) -> bytes:
        ...
    def get_code(self, code_hash: Bytes32) -> bytes:
        ...


# TODO: when to shut down the tracer, just in case of unexpected loop?
SANITY_LIMIT = 10000


@cli.command()
def gen():
    click.echo('generating fraud proof')
    # TODO
    src = HttpSource()

    init_step = Step()
    trac = CaptureTrace(src)
    trac.add_step(init_step)

    n = 0
    while True:
        n += 1

        if n >= SANITY_LIMIT:
            raise Exception("Oh no! So many steps! What happened?")

        # reset tracking of the nodes of all steps,
        # so we can capture which parts are accessed for the production of the new step
        trac.reset_shims()
        # Given the trace interface (last step + MPTs + code by hash), produce the new step
        new_step = next_step(trac)
        # capture which parts of the last step were accessed to create next_step
        trac.capture_access()
        # adds step, and a new trace entry to track what the step after will access
        trac.add_step(new_step)

        mode = ExecMode(trac.last().exec_mode)
        if exec_is_done(mode):
            break

    if len(trac.step_trace) != len(trac.access_trace):
        raise Exception("steps and access count different: %d <> %d" % (len(trac.step_trace), len(trac.access_trace)))

    def encode_hex(v: bytes) -> str:
        return '0x' + v.hex()

    binary_nodes = dict()

    def store_tree(b: PairNode):
        left, right = b.get_left(), b.get_right()
        # The merkle-roots are cached, this is fine
        binary_nodes[encode_hex(b.merkle_root())] = [encode_hex(left.merkle_root()), encode_hex(right.merkle_root())]
        if not left.is_leaf():
            store_tree(left)
        if not right.is_leaf():
            store_tree(right)

    access_per_step: List[StepAccessList] = []
    for i in range(n):
        step = trac.step_trace[i]
        acc_li = trac.access_trace[i]

        # Combine all different MPT witnesses, they are unique by hash anyway
        nodes = [encode_hex(n) for n in acc_li.accessed_world_mpt_nodes]
        for node_li in acc_li.accessed_acc_storage_mpt_nodes.values():
            nodes.extend([encode_hex(n) for n in node_li])

        access_per_step.append(StepAccessList(
            root=encode_hex(step.hash_tree_root()),
            accessed_gindices=[encode_hex(gi.to_bytes(length=32, byteorder='big')) for gi in acc_li.step_gindices],
            accessed_world_mpt_nodes=nodes,
            accessed_code_hashes=[encode_hex(h) for h in acc_li.accessed_codes],
        ))

        # store the nodes in a shared dict
        store_tree(step.get_backing())

    code_by_hash = {encode_hex(k): encode_hex(v) for k, v in trac.codes.items()}
    mpt_node_by_hash = {encode_hex(k): encode_hex(v) for k, v in trac.world_mpt.local_db.items()}

    trac_witness = TraceWitnessData(
        code_by_hash=code_by_hash,
        mpt_node_by_hash=mpt_node_by_hash,
        binary_nodes=binary_nodes,
        steps=access_per_step,
    )

    # TODO: use click file option flag (can also write to stdout with special flag value)
    click.echo(json.dumps(trac_witness))


@cli.command()
def step_witness():
    """Compute the witness data for a single step by index, using the full trace witness"""
    # TODO: load TraceWitnessData, run trace_witness.get_step_witness(i), dump output
    ...


@cli.command()
def verify():
    """Verify the execution of a step by providing the witness data and computing the step output"""
    click.echo('verifying fraud proof')
    # TODO
