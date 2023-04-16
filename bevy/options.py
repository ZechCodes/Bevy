from typing import Generic, TypeVar


_T = TypeVar("_T")


class Option(Generic[_T]):
    @property
    def value(self):
        raise Exception("No value was set")

    def value_or(self, default: _T) -> _T:
        return default

    def __bool__(self):
        return True

    def __repr__(self):
        return f"{type(self).__name__}()"

    def __str__(self):
        return f"<{type(self).__name__}>"


class Value(Option):
    __match_args__ = ("value",)

    def __init__(self, value: _T):
        self._value = value

    @property
    def value(self):
        return self._value

    def value_or(self, default: _T) -> _T:
        return self.value

    def __repr__(self):
        return f"{type(self).__name__}({self.value!r})"

    def __str__(self):
        return f"<{type(self).__name__}: {self.value!r}>"


class Null(Option):
    __match_args__ = ("message",)

    def __init__(self, message: str = ""):
        self.message = message

    def __bool__(self):
        return False

    def __repr__(self):
        return f"{type(self).__name__}({repr(self.message) or ''})"

    def __str__(self):
        message = f": {self.message}" if self.message else ""
        return f"<{type(self).__name__}{message}>"
