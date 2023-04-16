from contextvars import ContextVar as _ContextVar, Token as _Token
from typing import Callable, Generic, TypeVar


_T = TypeVar("_T")
_NOTSET = object()


class ContextVarDefaultFactory(Generic[_T]):
    """This contextvar wrapper uses a factory function to create the value of the context variable if it isn't already\
    set."""

    def __init__(self, name: str, *, default: Callable[[], _T]):
        self._var = _ContextVar(name, default=_NOTSET)
        self._factory = default

    @property
    def name(self) -> str:
        """Proxy the name of the contextvar"""
        return self._var.name

    def get(self) -> _T | None:
        """Proxy getting the value of the contextvar, setting the contextvar's value using the factory function if the
        contextvar is not already set."""
        value = self._var.get()
        if value is not _NOTSET:
            return value

        new_value = self._factory()
        self._var.set(new_value)
        return new_value

    def set(self, value: _T):
        """Proxy the contextvar's set method."""
        self._var.set(value)

    def reset(self, token: _Token[_T]) -> None:
        """Proxy the contextvar's reset method."""
        self._var.reset(token)
