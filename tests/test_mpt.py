from .test_proof_gen import TestMPT
from macula.mpt_work import mpt_hash, MPTAccessMode, mpt_step_with_trie
from macula.step import Step, uint256, MPTWorkScope
from macula.trace import StepsTrace


def test_mpt_read():
    mpt = TestMPT()
    mpt.insert(b'\x12\x34' + b'\x00'*30, b'\x55\x42\x54\x02')
    mpt.insert(b'\x12\x28' + b'\x22'*30, b'\x56\x42\x02\x44\x55')
    root = mpt.trie.root_hash
    step = Step(
        mpt_work=MPTWorkScope(
            mode=MPTAccessMode.READING.value,
            current_root=root,
            lookup_key=uint256(0x1234 << (256 - 4*4)),
            lookup_key_nibbles=64,
            lookup_nibble_depth=0,
            mode_on_finish=0xff,
        )
    )

    for i in range(512):
        if step.mpt_work.mode == 0xff:
            print("done!")
            if step.mpt_work.fail_lookup == 0:
                print("success! rlp value: %s" % step.mpt_work.value.hex())
            else:
                print("value not found, reason: %d" % step.mpt_work.fail_lookup)
            assert step.mpt_work.fail_lookup == 0
            return

        out = mpt_step_with_trie(step, mpt)
        print(out)
        step = out

    raise Exception("infinite loop? cut off at 512, abnormally large tree")
