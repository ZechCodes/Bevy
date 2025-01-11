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
    def __init__(self):
        self.hooks = set()

    def add_hook(self, hook: HookFunction):
        self.hooks.add(hook)

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


type _HookFunctionDecorator[**P, R] = Callable[[Callable[P, R]], HookWrapper[P, R]]


class HookDecoratorMeta(type):
    def __getattr__(cls, name):
        if hook := getattr(Hook, name, None):
            return cls(hook)

        return super().__getattribute__(name)


class HookDecorator[**P, R](metaclass=HookDecoratorMeta):
    GET_INSTANCE: _HookFunctionDecorator[P, R]
    GOT_INSTANCE: _HookFunctionDecorator[P, R]
    CREATE_INSTANCE: _HookFunctionDecorator[P, R]
    CREATED_INSTANCE: _HookFunctionDecorator[P, R]
    HANDLE_UNSUPPORTED_DEPENDENCY: _HookFunctionDecorator[P, R]

    def __init__(self, hook_type: Hook):
        self.hook_type = hook_type

    def __call__(self, func: Callable[P, R]) -> HookWrapper[P, R]:
        return HookWrapper(self.hook_type, func)


hooks = HookDecorator
