from typing import Generic, TypeVar


_T = TypeVar("_T")


class Option(Generic[_T]):
    def __new__(cls, *args, **kwargs):
        if cls is Option:
            raise Exception("You cannot create an instance of the base option type.")

        return object.__new__(cls)

    @property
    def value(self) -> _T:
        return self._get_value()

    def _get_value(self):
        raise Exception("No value was set")

    def value_or(self, default: _T) -> _T:
        return default

    def __bool__(self):
        return True

    def __repr__(self):
        return f"{type(self).__name__}()"

    def __str__(self):
        return f"<{type(self).__name__}>"


class Value(Option[_T]):
    __match_args__ = ("value",)

    def __init__(self, value: _T):
        self._value = value

    def _get_value(self):
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

    def _get_value(self):
        if self.message:
            raise Exception(self.message)

        super()._get_value()

    def __bool__(self):
        return False

    def __repr__(self):
        return f"{type(self).__name__}({repr(self.message) or ''})"

    def __str__(self):
        message = f": {self.message}" if self.message else ""
        return f"<{type(self).__name__}{message}>"
