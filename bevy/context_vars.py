import typing
from contextvars import ContextVar

if typing.TYPE_CHECKING:
    from bevy.containers import Container
    from bevy.registries import Registry

global_container: "ContextVar[Container]" = ContextVar("global_container")
global_registry: "ContextVar[Registry]" = ContextVar("global_registry")


def get_global_registry() -> "Registry":
    """Gets the global registry. If no registry exists, creates a new one."""
    try:
        registry = global_registry.get()
    except LookupError:
        global_registry.set(
            registry := Registry()
        )

    return registry


def get_global_container() -> "Container":
    """Gets the global container. If no container exists, creates a new one using the global registry."""
    try:
        container = global_container.get()
    except LookupError:
        global_container.set(
            container := get_global_registry().create_container()
        )

    return container


class GlobalContextMixin:
    """This mixin allows instances to be loaded into a predefined contextvar using a context manager."""
    def __init_subclass__(cls, *, var: ContextVar, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._context_var = var

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._reset_tokens = []

    def __enter__(self):
        self._reset_tokens.append(self._context_var.set(self))
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._context_var.reset(self._reset_tokens.pop())
