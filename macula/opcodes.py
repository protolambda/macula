from enum import Enum
from remerkleable.basic import uint8

class OpCode(Enum):
    STOP = 0
    CALL = 0xf1
    PUSH = 0x60
    # TODO

    def byte(self) -> uint8:
        return uint8(self.value)
