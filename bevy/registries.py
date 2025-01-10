from collections import defaultdict
from typing import Callable, Type, TYPE_CHECKING

from bevy.context_vars import ContextVarContextManager, global_registry
from bevy.hooks import Hook, HookFunction, HookManager
import bevy.containers as containers

type DependencyFactory[T] = "Callable[[containers.Container], T]"


class Registry(ContextVarContextManager, var=global_registry):
    def __init__(self):
        super().__init__()
        self.hooks: dict[Hook, HookManager] = defaultdict(HookManager)
        self.factories: "dict[Type[containers.Instance], DependencyFactory[containers.Instance]]" = {}

    def add_factory(self, factory: "DependencyFactory[containers.Instance]", for_type: "Type[containers.Instance]"):
        self.factories[for_type] = factory

    def add_hook(self, hook_type: Hook, hook: HookFunction):
        self.hooks[hook_type].add_hook(hook)

    def create_container(self) -> "containers.Container":
        return containers.Container(self)
