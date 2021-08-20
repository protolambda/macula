from typing import Callable, Protocol
from .step import Step


class StepsTrace(Protocol):
    def last(self) -> Step: ...
    def by_index(self) -> Step: ...
    def length(self) -> int: ...


Processor = Callable[[StepsTrace], Step]

