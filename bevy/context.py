from __future__ import annotations
from bevy.exception import BevyBaseException
from bevy.binder import Binder
from bevy.injector import Injector
from typing import Callable, Generic, Type, TypeVar, ParamSpec

T = TypeVar("T")
P = ParamSpec("P")


class Context:
    def __init__(self, parent: Context | None = None):
        self._parent = parent
        self._repository: list[Dependency] = []
        self._lookup_cache: dict[Type[T] | Injector[T], T] = {}

    def add(
        self, instance: T, *, use_as: type | None = None, ignore_hierarchy: bool = False
    ):
        """Adds an instance to the context repository."""
        self._repository.append(
            Dependency(instance, use_as=use_as, ignore_hierarchy=ignore_hierarchy)
        )

    def bind(self, instance_type: Type[T] | Binder[T]) -> Callable[[P], T]:
        """Creates a callable that returns instances of the given type that are bound to the context."""

        def builder(*args, **kwargs):
            instance = instance_type.__new__(instance_type, *args, **kwargs)
            instance.__bevy_context__ = self
            instance.__init__(*args, **kwargs)
            return instance

        if hasattr(instance_type, "__bevy_builder__"):
            builder = instance_type.__bevy_builder__(self)

        return builder

    def branch(self) -> Context:
        """Creates a context that inherits from the current context's repository."""
        return type(self)(self)

    def get(
        self, instance_type: Type[T] | Injector[T], *, propagate: bool = True
    ) -> T | None:
        """Gets an instance matching the given type."""
        if hasattr(instance_type, "__bevy_create__"):
            return instance_type.__bevy_create__(self)

        if instance_type not in self._lookup_cache and (
            match := self._get_match(instance_type)
        ):
            self._lookup_cache[instance_type] = match

        if propagate and self._parent and instance_type not in self._lookup_cache:
            return self._parent.get(instance_type)

        return self._lookup_cache.get(instance_type, None)

    def get_or_create(
        self, instance_type: Type[T] | Injector[T], *, propagate: bool = False
    ) -> T | None:
        """Gets an instance for the given type, if it isn't found an instance will be created and added to the
        repository."""
        if not (match := self.get(instance_type, propagate=propagate)):
            match = self.bind(instance_type)()
            self.add(match)

        return match

    def _get_match(self, instance_type: Type[T] | Injector[T]) -> T | None:
        for dependency in self._repository:
            if dependency.is_match(instance_type):
                return dependency.instance

        return None


class Dependency(Generic[T]):
    """Wraps each instance that has been added to the dependency repository. Handles determining matches."""

    def __init__(
        self, instance: T, *, use_as: type | None = None, ignore_hierarchy: bool = False
    ):
        self._ignore_hierarchy = ignore_hierarchy
        self._instance = instance
        self._type = use_as or type(instance)

    @property
    def instance(self) -> T:
        return self._instance

    def is_match(self, search: type | Injector) -> bool:
        """Checks if the instance's type matches the search. If the search implements the Injector prototype it will
        use its __bevy_matches__ method."""
        if hasattr(search, "__bevy_matches__"):
            return search.__bevy_matches__(self._type)

        if (
            self._type is not search
            and not self._ignore_hierarchy
            and issubclass(search, self._type)
        ):
            raise BevyUnsafeTypeHierarchy(
                f"{search} is a subclass of the type that has been registered with the context ({self._type}). This "
                f"could lead to unexpected behavior. Use the ignore_hierarchy option if this is not a concern."
            )

        return (
            self._type is search
            or issubclass(self._type, search)
            or (self._ignore_hierarchy and issubclass(search, self._type))
        )


class BevyUnsafeTypeHierarchy(BevyBaseException):
    ...
