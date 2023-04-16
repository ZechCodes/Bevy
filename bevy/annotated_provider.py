from typing import Annotated, Callable, Hashable, Type, TypeAlias, TypeVar, get_args

from bevy.providers import Provider, NotFound, NotSupported
from bevy.results import result

_T = TypeVar("_T")
_A: TypeAlias = Annotated[Type[_T], Hashable]


class AnnotatedProvider(Provider[_A, _T]):
    """The type provider supports any types and will attempt to instantiate them with no args."""

    def factory(self, annotated: _A) -> Callable[[], _T] | None:
        new_type, _ = get_args(annotated)
        return lambda: self._repository.get(new_type)

    @result
    def find(self, annotated: _A) -> _T | NotFound:
        try:
            return self._cache[annotated]
        except KeyError as exception:
            return NotFound(f"{type(self)!r} has no instances cached for {annotated!r}")

    @result
    def set(self, annotated: _A, value: _T) -> NotSupported | None:
        if (factory := self.factory(annotated)) is None:
            return NotSupported(f"{type(self)!r} does not support {annotated!r}")

        self._cache[annotated] = value
