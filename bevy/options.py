from abc import ABC, abstractmethod
from typing import Generic, TypeVar

_T = TypeVar("_T")


class Option(Generic[_T], ABC):
    """`Option` types help make code cleaner and typing more consistent. The `Value` option wraps values while the `Null`
    options stand in for no value. `Option` types are convenient to use with match/case statements.

    **Example**

        match result:
            case Value(value):
                ...
            case Null():
                ...
    """

    @property
    @abstractmethod
    def value(self) -> _T:
        """Returns the value assigned to the option. This raises `Exception` if accessed on a `Null` option."""

    @abstractmethod
    def value_or(self, default: _T) -> _T:
        """Returns the value if it is set, otherwise returns the provided default value."""


class Value(Option[_T]):
    """The `Value` option type is used to wrap a value. No matter what the value a `Value` option always evaluates as
    `True` to help identify if an `Option` has a value set. The `Value` option can surface its value as a match arg in a
    match/case statement.

    **Example**

        match example:
            case Value(value):
                print(value)
    """

    __match_args__ = ("value",)

    def __init__(self, value: _T):
        self._value = value

    @property
    def value(self) -> _T:
        """Gets the value assigned to the `Value` option."""
        return self._value

    def value_or(self, default: _T) -> _T:
        """`Value` option always have a value set, this always returns that value."""
        return self.value

    def __bool__(self):
        return True

    def __repr__(self):
        return f"{type(self).__name__}({self.value!r})"

    def __str__(self):
        return f"<{type(self).__name__}: {self.value!r}>"


class Null(Option):
    """The `Null` option type represents the absence of a value. The `Null` option will always evaluate as `False` to
    help identify if an `Option` has a value or not. `Null` options can take an optional message that will be used in
    error messages and that can be surfaced as a match arg in match/case statements.

    **Example**

        match example:
            case Null(message):
                print(message)
    """

    __match_args__ = ("message",)

    def __init__(self, message: str = ""):
        self._message = message

    @property
    def message(self) -> str:
        """The exception message the `Null` option will use if the value is accessed."""
        return self._message or "The value is null"

    @property
    def value(self):
        """The `Null` options never have values so this raises an `Exception` containing the `Null` option's message."""
        raise Exception(self.message)

    def value_or(self, default: _T) -> _T:
        """`Null` options never have a value so this only returns `default`."""
        return default

    def __bool__(self):
        return False

    def __repr__(self):
        return f"{type(self).__name__}({repr(self._message) if self._message else ''})"

    def __str__(self):
        message = f": {self._message}" if self._message else ""
        return f"<{type(self).__name__}{message}>"
