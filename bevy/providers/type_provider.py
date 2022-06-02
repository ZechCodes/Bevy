from typing import Sequence, TypeVar

from bevy.inject import Bevy
from bevy.providers.protocol import ProviderProtocol
from bevy.sentinel import sentinel


KeyObject = TypeVar("KeyObject")
ValueObject = TypeVar("ValueObject")
T = TypeVar("T")


NOT_FOUND = sentinel("NOT_FOUND")


class TypeProvider(ProviderProtocol, Bevy):
    def __init__(self, *_, **__):
        super().__init__()
        self._repository = {}

    def add(self, obj: ValueObject, *, use_as: KeyObject | None = None):
        key = use_as or type(obj)
        self._repository[key] = obj

    def bind_to_context(self, obj: KeyObject | type, context) -> KeyObject | type:
        return type(obj.__name__, (obj,), {"__bevy_context__": context})

    def create(self, obj: KeyObject, *args, add: bool = False, **kwargs) -> ValueObject:
        value = self.bevy.bind(obj)(*args, **kwargs)
        if add:
            self.add(value)

        return value

    def get(self, obj: KeyObject, default: ValueObject | T | None = None) -> ValueObject | T | None:
        for key, value in self._repository.items():
            if obj is key or (isinstance(obj, type) and (issubclass(obj, key) or issubclass(key, obj))):
                return value

        return default

    def has(self, obj: KeyObject) -> bool:
        return self.get(obj, NOT_FOUND) is not NOT_FOUND

    def supports(self, obj: KeyObject) -> bool:
        return isinstance(obj, type)

    @classmethod
    def create_and_insert(
        cls,
        providers: Sequence[ProviderProtocol],
        *args,
        **kwargs
    ) -> Sequence[ProviderProtocol]:
        return *providers, cls(*args, **kwargs)
