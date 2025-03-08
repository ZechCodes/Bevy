from enum import Enum
from typing import Any, Callable, Type, TYPE_CHECKING
import functools

from tramp.optionals import Optional

import bevy.registries as r

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
    """A utility type that makes it easier to work with collections of functions waiting for the
    hook to be triggered."""
    def __init__(self):
        self.callbacks = set()

    def add_callback(self, hook: HookFunction):
        """Adds a function that will be called when the hook is triggered."""
        self.callbacks.add(hook)

    def handle[T](self, container: "Container", value: T) -> Optional[Any]:
        """Iterates each callback and returns the first result."""
        for callback in self.callbacks:
            match callback(container, value):
                case Optional.Some() as v:
                    return v

        return Optional.Nothing()

    def filter[T](self, container: "Container", value: T) -> T:
        """Iterates all callbacks and updates the value when a callback returns a Some result."""
        for callback in self.callbacks:
            match callback(container, value):
                case Optional.Some(v):
                    value = v
                case Optional.Nothing():
                    pass

        return value


class HookWrapper[**P, R]:
    __match_args__ = ("hook_type",)

    def __init__(self, hook_type: Hook, func: Callable[P, R]):
        self.hook_type = hook_type
        self.func = func

        functools.update_wrapper(self, func)

    def __call__(self, container: "Container", value: P) -> Optional[R]:
        return self.func(container, value)

    def register_hook(self, registry: "r.Registry | None" = None):
        registry = r.get_registry(registry)
        registry.add_hook(self)


class _HookDecoratorDescriptor:
    def __init__(self):
        self.hook_type: Optional[Hook] = Optional.Nothing()

    def __get__(self, instance, owner):
        return HookDecorator(self.hook_type.value)

    def __set_name__(self, owner, name):
        self.hook_type = Optional.Some(Hook[name])


class HookDecorator[**P, R]:

    GET_INSTANCE = _HookDecoratorDescriptor()
    GOT_INSTANCE = _HookDecoratorDescriptor()
    CREATE_INSTANCE = _HookDecoratorDescriptor()
    CREATED_INSTANCE = _HookDecoratorDescriptor()
    HANDLE_UNSUPPORTED_DEPENDENCY = _HookDecoratorDescriptor()

    def __init__(self, hook_type: Hook):
        self.hook_type = hook_type

    def __call__(self, func: Callable[P, R]) -> HookWrapper[P, R]:
        return HookWrapper(self.hook_type, func)


hooks = HookDecorator
