from contextvars import ContextVar as _ContextVar, Token as _Token
from typing import Callable, Generic, TypeVar

from bevy.options import Option as _Option, Value as _Value, Null as _Null

_T = TypeVar("_T")


class ContextVarDefaultFactory(Generic[_T]):
    """This contextvar wrapper uses a factory function to create the value of the context variable if it isn't already\
    set."""

    def __init__(self, name: str, *, default: Callable[[], _T]):
        self._var: _ContextVar[_Option[_T]] = _ContextVar(name, default=_Null())
        self._factory = default

    @property
    def name(self) -> str:
        """Proxy the name of the contextvar."""
        return self._var.name

    def get(self) -> _T | None:
        """Proxy getting the value of the contextvar, setting the contextvar's value using the factory function if the
        contextvar is not already set."""
        match self._var.get():
            case _Value(value):
                return value

            case _Null():
                return self._setup()

    def set(self, value: _T):
        """Proxy the contextvar's set method."""
        self._var.set(_Value(value))

    def reset(self, token: _Token[_T]) -> None:
        """Proxy the contextvar's reset method."""
        self._var.reset(token)

    def _setup(self) -> _T:
        """Create the default value and assign it to the contextvar."""
        value = self._factory()
        self.set(value)
        return value
