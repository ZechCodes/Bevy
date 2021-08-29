from typing import Optional, Protocol, runtime_checkable


@runtime_checkable
class Reader(Protocol):
    file_type: str

    def read(self) -> str:
        ...

    def save(self, data: str):
        ...


def is_reader(obj):
    return isinstance(obj, Reader)


@runtime_checkable
class Resolver(Protocol):
    def __init__(self, directory):
        ...

    def get_file_reader(
        self, filename: str, file_types: tuple[str]
    ) -> Optional[Reader]:
        ...


def is_resolver(obj):
    return isinstance(obj, Resolver)
