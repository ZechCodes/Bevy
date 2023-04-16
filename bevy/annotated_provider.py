from bevy.providers import Provider
from typing import Annotated, Callable, Hashable, Type, TypeAlias, TypeVar, get_args
from bevy.results import Result, ResultBuilder


_T = TypeVar("_T")
_A: TypeAlias = Annotated[Type[_T], Hashable]


class AnnotatedProvider(Provider[_A, _T]):
    """The type provider supports any types and will attempt to instantiate them with no args."""

    def set(self, annotated: _A, value: _T) -> Result[bool]:
        with ResultBuilder() as (result_builder, set_result):
            if (builder := self.builder(annotated)) is None:
                raise Exception(f"The provider does not support {annotated!r}")

            self._cache[annotated] = value
            set_result(True)

        return result_builder.result

    def builder(self, annotated: _A) -> Callable[[], _T] | None:
        new_type, _ = get_args(annotated)
        return lambda: self._repository.get(new_type)

    def find(self, annotated: _A) -> Result[_T]:
        with ResultBuilder() as (builder, set_result):
            try:
                set_result(self._cache[annotated])
            except KeyError as exception:
                raise Exception(
                    f"Provider had no instances cached for {annotated!r}"
                ) from exception

        return builder.result
