from typing import Literal

from bevy.base_context import BaseContext


class NullContext(BaseContext):
    def add_provider(self, *_, **__) -> None:
        return None

    def branch(self) -> BaseContext:
        return self

    def get_provider(self, *_, **__) -> None:
        return None

    def get_provider_for(self, *_, **__) -> None:
        return None

    def get(self, *_, **__) -> None:
        return None

    def has_provider(self, *_, **__) -> Literal[False]:
        return False

    def __bool__(self):
        return False
