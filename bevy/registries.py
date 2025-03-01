from collections import defaultdict
from typing import overload, Type, TYPE_CHECKING

from bevy.context_vars import GlobalContextMixin, get_global_registry, global_registry
import bevy.containers as containers
import bevy.hooks as hooks
from bevy.factories import Factory

type DependencyFactory[T] = "Callable[[containers.Container], T]"


class Registry(GlobalContextMixin, var=global_registry):
    def __init__(self):
        super().__init__()
        self.hooks: dict[hooks.Hook, hooks.HookManager] = defaultdict(hooks.HookManager)
        self.factories: "dict[Type[containers.Instance], DependencyFactory[containers.Instance]]" = {}

    @overload
    def add_factory(self, factory: "DependencyFactory[containers.Instance]", for_type: "Type[containers.Instance]"):
        ...

    @overload
    def add_factory(self, factory: "Factory"):
        ...

    def add_factory(self, *args):
        match args:
            case [Factory() as factory]:
                factory.register_factory(self)

            case [factory, type() as for_type] if callable(factory):
                self.factories[for_type] = factory

            case _:
                raise ValueError(f"Unexpected arguments to add_factory: {args}")

    @overload
    def add_hook(self, hook: "hooks.HookWrapper"):
        ...

    @overload
    def add_hook(self, hook_type: "hooks.Hook", hook: "hooks.HookFunction"):
        ...

    def add_hook(self, *args):
        match args:
            case [hooks.Hook() as hook_type, hook] if callable(hook):
                self.hooks[hook_type].add_hook(hook)

            case [hooks.HookWrapper(hook_type) as hook]:
                self.hooks[hook_type].add_hook(hook)

            case _:
                raise ValueError(f"Unexpected arguments to add_hook: {args}")


    def create_container(self) -> "containers.Container":
        return containers.Container(self)


def get_registry(registry: Registry | None = None) -> Registry:
    if registry is not None:
        return registry

    registry = get_global_registry()
    if registry is None:
        registry = Registry()

    return registry
