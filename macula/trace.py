from typing import Callable, Protocol
from macula.step import Step


class StepsTrace(Protocol):
    def last(self) -> Step: ...
    def by_index(self) -> Step: ...
    def length(self) -> int: ...


Processor = Callable[[StepsTrace], Step]

