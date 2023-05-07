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
from bevy.providers.provider import Provider
from bevy.repository_cache import RepositoryCache as _RepositoryCache

_T = TypeVar("_T")
_A: TypeAlias = Annotated[Type[_T], Hashable]


def get_type(annotated: _A) -> Option[_T]:
    """Get the type being annotated by a typing.Annotated instance."""
    match get_args(annotated):
        case (type() as type_, _):
            return Value(type_)
        case _:
            return Null()


class AnnotatedProvider(Provider[_A, _T]):
    """The annotated provider supports typing.Annotated annotations. It will attempt to instantiate the annotated type
    if it's not found in the cache."""

    def factory(
        self, key: _A, cache: _RepositoryCache[_A, _T]
    ) -> Option[Callable[[], _T]]:
        """Get a callable for getting or constructing an instance of the annotated type. This will call the repository's
        get method looking up the un-annotated type, this will attempt to instantiate an instance of the type if no
        providers have an instance cached."""
        match get_type(key):
            case Value(type_):
                return Value(partial(cache.repository.get, type_))
            case Null(message):
                return Null(message)

    def supports(self, key: _A, _) -> bool:
        """Checks if the given key is indeed a typing.Annotated wrapped type."""
        return bool(get_type(key)) and get_origin(key) is Annotated
