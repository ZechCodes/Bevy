from __future__ import annotations
from bevy.context.abstract_context import AbstractContext
from bevy.single_return_value_cache import single_return_value_cache


class NullContext(AbstractContext):
    def add(self, *_, **__) -> None:
        return None

    def add_provider(self, *_, **__) -> None:
        return None

    def bind(self, *_, **__) -> None:
        return

    def branch(self) -> AbstractContext:
        return self

    def create(self, *_, **__) -> None:
        return None

    def get(self, *_, **__) -> None:
        return None

    def get_provider_for(self, *_, **__) -> None:
        return None

    def has(self, *_, **__) -> None:
        return

    def has_provider_for(self, *_, **__) -> None:
        return

    @classmethod
    @single_return_value_cache
    def factory(cls, *_) -> NullContext:
        return cls()

    def __bool__(self):
        return False
