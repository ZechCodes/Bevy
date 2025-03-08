from collections import defaultdict
from typing import overload, Type

import bevy.containers as containers
import bevy.hooks as hooks
from bevy.context_vars import get_global_registry, global_registry, GlobalContextMixin
from bevy.factories import Factory

type DependencyFactory[T] = "Callable[[containers.Container], T]"


class Registry(GlobalContextMixin, var=global_registry):
    """Registries hold factories and hooks for creating and managing instances of objects. Containers are created from
    registries, and containers are used to create and cache instances of objects."""
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
        """Adds a factory to the registry. Factories are used to create instances of objects. If an instance of Factory
        is passed its register_factory method is called to register it with the registry. If a callable and type is
        passed, the callable is stored as a factory for the type."""
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
    def add_hook(self, hook_type: "hooks.Hook", func: "hooks.HookFunction"):
        ...

    def add_hook(self, *args):
        """Adds a callback to a hook. If a HookWrapper is passed, the hook is added to the registry. If a Hook type and
        a callable are passed, the callable is added as a callback to the hook."""
        match args:
            case [hooks.Hook() as hook_type, func] if callable(func):
                self.hooks[hook_type].add_callback(func)

            case [hooks.HookWrapper(hook_type) as hook]:
                self.hooks[hook_type].add_callback(hook)

            case _:
                raise ValueError(f"Unexpected arguments to add_hook: {args}")


    def create_container(self) -> "containers.Container":
        """Creates a new container bound to the registry."""
        return containers.Container(self)


@overload
def get_registry(registry: Registry | None) -> Registry:
    ...


@overload
def get_registry() -> Registry:
    ...


def get_registry(*args) -> Registry:
    """Returns a registry. If a registry is passed, it is returned. If no registry is passed or None is passed, the
    global registry is returned. This creates a new global registry if it is needed and doesn't already exist."""
    match args:
        case [Registry() as registry]:
            return registry

        case [None]:
            return get_global_registry()

        case []:
            return get_global_registry()

        case _:
            raise ValueError(f"Unexpected arguments to get_registry: {args}")


