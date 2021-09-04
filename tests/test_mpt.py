from .test_proof_gen import TestMPT
from macula.mpt_proof_trace import mpt_hash, MPTAccessMode, make_mpt_step_gen
from macula.step import Step, uint256
from macula.trace import StepsTrace


# No full trace, just return a single step last step for debugging purposes.
class SingleStepTrace(StepsTrace):
    step: Step

    def __init__(self, step: Step):
        self.step = step

    def last(self) -> Step:
        return self.step


def test_mpt_read():
    mpt = TestMPT()
    mpt.insert(b'\x12\x34', b'\x55\x42\x54\x02')
    mpt.insert(b'\x12\x28', b'\x56\x42\x02')
    root = mpt.trie.root_hash
    step = Step(
        mpt_mode=MPTAccessMode.READING.value,
        mpt_current_root=root,
        mpt_lookup_key=uint256(0x1234 << (256 - 4*4)),
        mpt_lookup_key_nibbles=4,
        mpt_lookup_nibble_depth=0,
    )
    step_fn = make_mpt_step_gen(mpt)
    trac = SingleStepTrace(step)
    out = step_fn(trac)
    print(out)

