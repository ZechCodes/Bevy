from contextvars import ContextVar as _ContextVar, Token as _Token
from typing import Callable, Generic, TypeVar


_T = TypeVar("_T")
_NOTSET = object()


class ContextVarDefaultFactory(Generic[_T]):
    def __init__(self, name: str, *, default: Callable[[], _T]):
        self._var = _ContextVar(name, default=_NOTSET)
        self._factory = default

    @property
    def name(self) -> str:
        return self._var.name

    def get(self) -> _T | None:
        value = self._var.get()
        if value is not _NOTSET:
            return value

        new_value = self._factory()
        self._var.set(new_value)
        return new_value

    def set(self, value: _T):
        self._var.set(value)

    def reset(self, token: _Token[_T]) -> None:
        self._var.reset(token)
