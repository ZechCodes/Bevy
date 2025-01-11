from collections import defaultdict
from typing import overload, Type

from bevy.context_vars import ContextVarContextManager, get_global_registry, global_registry
import bevy.containers as containers
import bevy.hooks as hooks

type DependencyFactory[T] = "Callable[[containers.Container], T]"


class Registry(ContextVarContextManager, var=global_registry):
    def __init__(self):
        super().__init__()
        self.hooks: dict[hooks.Hook, hooks.HookManager] = defaultdict(hooks.HookManager)
        self.factories: "dict[Type[containers.Instance], DependencyFactory[containers.Instance]]" = {}

    def add_factory(self, factory: "DependencyFactory[containers.Instance]", for_type: "Type[containers.Instance]"):
        self.factories[for_type] = factory

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
