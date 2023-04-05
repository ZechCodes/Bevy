from typing import Generic, TypeVar


T = TypeVar("T")


class Provider(Generic[T]):
    ...
