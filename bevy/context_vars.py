import os
from contextvars import ContextVar

import bevy.containers as c
import bevy.registries as r

global_container: "ContextVar[c.Container]" = ContextVar("global_container")
global_registry: "ContextVar[r.Registry]" = ContextVar("global_registry")


class GlobalContextDisabledError(Exception):
    """Raised when the global context is disabled by the BEVY_ENABLE_GLOBAL_CONTEXT environment variable."""


yes_no_mapping = {
    "yes": True,
    "no": False,
    "true": True,
    "false": False,
    "1": True,
    "0": False,
    "y": True,
    "n": False,
}


def is_global_context_enabled() -> bool:
    """Returns True if the global context is enabled, False otherwise."""
    var = os.getenv("BEVY_ENABLE_GLOBAL_CONTEXT", "yes")
    return yes_no_mapping.get(var.casefold(), True)


def get_global_registry() -> "r.Registry":
    """Gets the global registry. If no registry exists, creates a new one. Raises GlobalContextNotAllowedError if the
    BEVY_ALLOW_GLOBAL_CONTEXT environment variable is set to False."""
    if not is_global_context_enabled():
        raise GlobalContextDisabledError("Global context is disabled. You must provide a registry to use.")

    try:
        registry = global_registry.get()
    except LookupError:
        global_registry.set(
            registry := r.Registry()
        )

    return registry


def get_global_container() -> "c.Container":
    """Gets the global container. If no container exists, creates a new one using the global registry. Raises
    GlobalContextNotAllowedError if the BEVY_ALLOW_GLOBAL_CONTEXT environment variable is set to False."""
    if not is_global_context_enabled():
        raise GlobalContextDisabledError("Global context is disabled. You must provide a container to use.")

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
