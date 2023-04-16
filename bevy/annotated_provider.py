from functools import partial
from typing import (
    Annotated,
    Callable,
    Hashable,
    Type,
    TypeAlias,
    TypeVar,
    get_args,
    get_origin,
)

from bevy.options import Option, Value, Null
from bevy.providers import Provider

_T = TypeVar("_T")
_A: TypeAlias = Annotated[Type[_T], Hashable]


def get_type(annotated: _A) -> Option[_T]:
    match get_args(annotated):
        case (type() as new_type, _):
            return Value(new_type)
        case _:
            return Null()


class AnnotatedProvider(Provider[_A, _T]):
    """The type provider supports any types and will attempt to instantiate them with no args."""

    def factory(self, annotated: _A) -> Option[Callable[[], _T]]:
        match get_type(annotated):
            case Value(new_type):
                return Value(partial(self._repository.get, new_type))
            case Null(message):
                return Null(message)

    def supports(self, annotated: _A) -> bool:
        if get_origin(annotated) is not Annotated:
            return False

        return isinstance(get_type(annotated).value_or(None), type)
