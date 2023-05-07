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
from bevy.provider_state import ProviderState as _ProviderState
from bevy.providers.provider import Provider

_T = TypeVar("_T")
_A: TypeAlias = Annotated[Type[_T], Hashable]


def _get_type(annotated: _A) -> Option[_T]:
    """Get the type being annotated by a typing.Annotated instance."""
    match get_args(annotated):
        case (type() as type_, _):
            return Value(type_)
        case _:
            return Null()


class AnnotatedProvider(Provider[_A, _T]):
    """The annotated provider supports `typing.Annotated` annotations. It will attempt to instantiate the annotated type
    if it's not found in the cache.

    **Example**

        @inject
        def example(
            arg: Annotated[Dependency, "example-annotation"] = dependency()
        ):
            ...
    """

    def factory(
        self, key: _A, cache: _ProviderState[_A, _T]
    ) -> Option[Callable[[], _T]]:
        """Returns a callable that will get or construct an instance of the annotated type. If no instances exist in the
        repository matching the annotation, this will call the `Repository.get` method looking for the un-annotated
        type. That will attempt to instantiate an instance of the type if no providers have an instance cached.
        """
        match _get_type(key):
            case Value(type_):
                return Value(partial(cache.repository.get, type_))
            case Null(message):
                return Null(message)

    def supports(self, key: _A, _) -> bool:
        """Only allows the `AnnotatedProvider` to work with `typing.Annotated` wrapped types."""
        return bool(_get_type(key)) and get_origin(key) is Annotated
