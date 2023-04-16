from abc import ABC, abstractmethod
from typing import Generic, TypeVar

_T = TypeVar("_T")


class Option(Generic[_T], ABC):
    """Option types help make code cleaner and typing more consistent. The value type can wrap values while the null
    type can stand in for anytime that there is no value set. Option types are convenient to use with match/case
    statements."""

    @property
    @abstractmethod
    def value(self) -> _T:
        return self._get_value()

    @abstractmethod
    def value_or(self, default: _T) -> _T:
        """Returns the value if it is set or returns the provided default value."""


class Value(Option[_T]):
    """The Value option type is used to wrap a set value. No matter what the contained value is instances of the Value
    type will always evaluate as truthyto help identify if an Option has a value or not. The Value type can surface its
    value as a match arg in a match/case statement.

        match example:
            case Value(value):
                print(value)
    """

    __match_args__ = ("value",)

    def __init__(self, value: _T):
        self._value = value

    @property
    def value(self) -> _T:
        return self._value

    def value_or(self, default: _T) -> _T:
        """The Value option will always have a value so this just returns the value."""
        return self.value

    def __bool__(self):
        return True

    def __repr__(self):
        return f"{type(self).__name__}({self.value!r})"

    def __str__(self):
        return f"<{type(self).__name__}: {self.value!r}>"


class Null(Option):
    """The Null option type represents the absence of a value. The Null option will always evaluate as falsey to help
    identify if an Option has a value or not. Null options can take an optional message that will be used in error
    messages and that can be surfaced as a match arg in match/case statements.

        match example:
            case Null(message):
                print(message)
    """

    __match_args__ = ("message",)

    def __init__(self, message: str = ""):
        self._message = message

    @property
    def message(self) -> str:
        return self._message or "Null value"

    @property
    def value(self):
        raise Exception(self.message)

    def value_or(self, default: _T) -> _T:
        """The Null option will never have a value so this just returns the default."""
        return default

    def __bool__(self):
        return False

    def __repr__(self):
        return f"{type(self).__name__}({repr(self._message) if self._message else ''})"

    def __str__(self):
        message = f": {self._message}" if self._message else ""
        return f"<{type(self).__name__}{message}>"
