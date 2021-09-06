import click
from typing import List, BinaryIO
from .exec_mode import ExecMode, exec_is_done
from .step import Step
from .capture import CaptureTrace
from .interpreter import next_step
from .witness import TraceWitnessData, StepAccessList
from .external import HttpSource
from .tx import load_tx
from remerkleable.tree import PairNode
import json


@click.group()
def cli():
    """Macula - optimistic rollup tech for ethereum
    Contribute here: https://github.com/protolambda/macula
    """


# TODO: when to shut down the tracer, just in case of unexpected loop?
SANITY_LIMIT = 10000


@cli.command()
@click.argument('output', type=click.File('wb'))
@click.argument('api', type=click.STRING, help="API endpoint to fetch state trie and contract code from")
@click.argument('tx', type=click.STRING, help="RLP encoded transaction, hex")  # TODO: replace with full RLP encoded block
def gen(output: BinaryIO, api: str, tx: str):
    """Generate a fraud proof for the given transaction"""

    click.echo("preparing trace...")
    src = HttpSource(api)
    trac = CaptureTrace(src)

    click.echo("decoding transaction: "+tx)
    if tx.startswith("0x"):
        tx = tx[2:]

    tx_bytes = bytes.fromhex(tx)

    click.echo("loading first step...")
    init_step = Step()
    load_tx(init_step, tx_bytes)  # TODO: we only load a single tx, not a full block yet
    trac.add_step(init_step)

    click.echo("running step by step proof generator...")
    n = 0
    while True:
        click.echo("\rProcessing step %d" % n, nl=False)
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

    click.echo("generated %d steps!" % n)

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

    click.echo("formatting witness data...")

    access_per_step: List[StepAccessList] = []
    for i in range(n):
        click.echo("\rProcessing step witness %d" % n, nl=False)

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

    click.echo("writing witness data...")
    json.dump(trac_witness, output)
    click.echo("done!")


@cli.command()
@click.argument('input', type=click.File('rb'))
@click.argument('output', type=click.File('wb'))
@click.argument('step', type=click.INT)
def step_witness(input: BinaryIO, step: int, output: BinaryIO):
    """Compute the witness data for a single step by index, using the full trace witness"""
    obj = json.load(input)
    trace_witness_data = TraceWitnessData(**obj)
    step_witness_data = trace_witness_data.get_step_witness(step)
    json.dump(step_witness_data, output)


@cli.command()
def verify():
    """Verify the execution of a step
    \f
    by providing the witness data and computing the step output"""
    click.echo('verifying fraud proof')
    # TODO
