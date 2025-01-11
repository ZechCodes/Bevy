from enum import Enum
from typing import Any, Callable, Type, TYPE_CHECKING

from tramp.optionals import Optional

if TYPE_CHECKING:
    from bevy.containers import Container

type HookFunction[T] = "Callable[[Container, Type[T]], T]"


class Hook(Enum):
    GET_INSTANCE = "get_instance"
    GOT_INSTANCE = "got_instance"
    CREATE_INSTANCE = "create_instance"
    CREATED_INSTANCE = "created_instance"
    HANDLE_UNSUPPORTED_DEPENDENCY = "handle_unsupported_dependency"


class HookManager:
    def __init__(self):
        self.hooks = set()

    def add_hook(self, hook: HookFunction):        self.hooks.add(hook)

    def handle[T](self, container: "Container", value: T) -> Optional[Any]:
        for hook in self.hooks:
            match hook(container, value):
                case Optional.Some() as v:
                    return v

        return Optional.Nothing()

    def filter[T](self, container: "Container", value: T) -> T:
        for hook in self.hooks:
            match hook(container, value):
                case Optional.Some(v):
                    value = v
                case Optional.Nothing():
                    pass

        return value