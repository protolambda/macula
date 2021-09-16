from typing import Protocol
from .step import Bytes32, Address


class ExternalSource(Protocol):
    def block_header(self, block_hash: Bytes32) -> bytes:
        raise NotImplementedError

    def get_acc_storage_node(self, addr: Address, key: Bytes32) -> bytes:
        raise NotImplementedError

    def get_world_node(self, key: Bytes32) -> bytes:
        raise NotImplementedError

    def get_code(self, code_hash: Bytes32) -> bytes:
        raise NotImplementedError


class HttpSource(ExternalSource):
    api_addr: str

    def __init__(self, api_addr: str):
        self.api_addr = api_addr

    # TODO: http client
    def block_header(self, block_hash: Bytes32) -> bytes:
        ...

    def get_acc_storage_node(self, addr: Address, key: Bytes32) -> bytes:
        ...
    def get_world_node(self, key: Bytes32) -> bytes:
        ...
    def get_code(self, code_hash: Bytes32) -> bytes:
        ...



