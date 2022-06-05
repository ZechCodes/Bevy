from typing import Sequence, TypeVar

from bevy.inject import Bevy
from bevy.providers.protocol import ProviderProtocol
from bevy.providers.injection_priority_helpers import high_priority
from bevy.sentinel import sentinel


KeyObject = TypeVar("KeyObject")
ValueObject = TypeVar("ValueObject")
T = TypeVar("T")


NOT_FOUND = sentinel("NOT_FOUND")


class InstanceProvider(ProviderProtocol, Bevy):
    def __init__(self, *_, **__):
        super().__init__()
        self._repository = {}

    def add(self, obj: ValueObject, *, use_as: KeyObject | None = None):
        self._repository[use_as or obj] = obj

    def bind_to_context(self, obj: KeyObject, context) -> KeyObject:
        raise Exception("Cannot bind instances to a context")

    def create(self, obj: KeyObject, *args, add: bool = False, **kwargs) -> ValueObject:
        if add:
            self.add(obj)

        return obj

    def get(self, obj: KeyObject, default: ValueObject | T | None = None) -> ValueObject | T | None:
        for key, value in self._repository.items():
            if obj is key:
                return value

        return default

    def has(self, obj: KeyObject) -> bool:
        return self.get(obj, NOT_FOUND) is not NOT_FOUND

    def supports(self, obj: KeyObject) -> bool:
        return not isinstance(obj, type)

    create_and_insert = high_priority
