from __future__ import annotations
from typing import Any, Generic, Optional, Sequence, Type, TypeVar, Union
from weakref import WeakKeyDictionary


__all__ = ("Context",)


T = TypeVar("T")
NOT_SET = object()


class Context:
    __slots__ = ("_parent", "_repository")

    def __init__(self, parent: Optional[Context] = None):
        self._parent = parent or NullContext()
        self._repository: set[ContextInstanceWrapper] = set()

    @property
    def parent(self) -> Optional[Context]:
        return self._parent

    def add(
        self,
        instance: T,
        *,
        as_type: Optional[Type] = None,
        labels: Sequence[str] = tuple()
    ):
        self._repository.add(
            ContextInstanceWrapper(instance, as_type or type(instance), labels)
        )

    def branch(self) -> Context:
        return Context(self)

    def build(self, build_type: Type[T], *args, **kwargs) -> T:
        instance = build_type.__new__(build_type, *args, **kwargs)
        self._add_context(instance)
        self._build_dependencies(instance)
        instance.__init__(*args, **kwargs)
        return instance

    def get(
        self,
        lookup_type: Type[T],
        *,
        propagate: bool = True,
        default: Any = NOT_SET,
        labels: Optional[set[str]] = None
    ) -> Optional[T]:
        match = self._find_match(lookup_type, labels or set(), propagate)
        if match:
            return match

        if default is NOT_SET:
            return None

        return default

    def has(self, lookup_type: Type[T], *, propagate: bool = True) -> bool:
        return bool(self._find_match(lookup_type, propagate))

    def _add_context(self, instance):
        if not hasattr(type(instance), "__bevy_context__"):
            type(instance).__bevy_context__ = ContextDescriptor()
        instance.__bevy_context__ = self

    def _build_dependencies(self, instance):
        for dependency in getattr(instance, "__bevy_dependencies__", []):
            dependency.get(instance)

    def _find_match(
        self, lookup_type: Type[T], labels: set[str], propagate: bool
    ) -> Optional[T]:
        for wrapper in self._repository:
            if wrapper.matches(lookup_type, labels):
                return wrapper.instance

        return self._parent.get(lookup_type) if propagate else None


class NullContext(Context):
    def __init__(self):
        pass

    def get(
        self, lookup_type: Type[T], *, propagate: bool = True, default: Any = NOT_SET
    ) -> Optional[T]:
        return None

    def has(self, lookup_type: Type[T], *, propagate: bool = True) -> bool:
        return False


class ContextDescriptor:
    def __init__(self):
        self._contexts = WeakKeyDictionary()

    def __get__(self, inst, owner):
        if not inst:
            return self
        return self._contexts.get(inst)

    def __set__(self, inst, value):
        if inst:
            self._contexts[inst] = value


class ContextInstanceWrapper(Generic[T]):
    def __init__(
        self, instance: T, as_type: Union[Type[T], Type], labels: Sequence[str]
    ):
        self._instance = instance
        self._as_type = as_type
        self._labels = self._clean_labels(labels)

    @property
    def instance(self) -> T:
        return self._instance

    @property
    def labels(self) -> set[str]:
        return self._labels

    def matches(self, match_type: Type, labels: Optional[set[str]] = None) -> bool:
        return (
            issubclass(match_type, self._as_type)
            or issubclass(self._as_type, match_type)
        ) and self._labels == self._clean_labels(labels)

    def __eq__(self, other):
        return self._as_type is other and self.labels == other.labels

    def __hash__(self):
        return hash(self._as_type)

    def _clean_labels(self, labels) -> set[str]:
        return {label.casefold() for label in labels}
