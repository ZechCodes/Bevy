from __future__ import annotations
from abc import ABC, abstractmethod
from bevy.context import Context
from typing import (
    Any,
    Generic,
    get_type_hints,
    Optional,
    Sequence,
    Type,
    TypeVar,
    Union,
)
from weakref import WeakKeyDictionary


T = TypeVar("T")


class Injectable(ABC):
    def __init__(self):
        self._instances = WeakKeyDictionary()

    def __get__(self, instance, owner):
        if not instance:
            return self

        return self.get(instance)

    def __set_name__(self, owner, name):
        deps = _get_dependencies(owner)
        deps.add(self)

    def get(self, instance: T) -> Any:
        if instance not in self._instances:
            self._instances[instance] = self.__bevy_inject__(
                instance, self._get_context(instance)
            )

        return self._instances[instance]

    @abstractmethod
    def __bevy_inject__(self, instance: T, context: Context) -> Any:
        ...

    def _get_context(self, instance) -> Context:
        context = getattr(instance, "__bevy_context__", None)
        if not context:
            raise NotBoundToAContext(f"{instance} is not bound to a Bevy context.")

        return context


class Inject(Injectable, Generic[T]):
    def __init__(
        self,
        dependency_type: Type[T],
        labels: Sequence[str] = tuple(),
        *,
        store: bool = True,
        as_type: Optional[Type] = None,
    ):
        self._type = dependency_type
        self._as_type = as_type or dependency_type
        self._store = store
        self._labels = labels

        self._instances = WeakKeyDictionary()

    def __class_getitem__(
        cls, item: Union[Type[T], tuple[Type[T], Sequence[str]]]
    ) -> Inject[T]:
        dependency_type, labels = item if isinstance(item, tuple) else (item, tuple())
        return Inject(dependency_type, labels)

    def __bevy_inject__(self, instance: T, context: Context):
        inst = context.get(self._as_type)
        if not inst:
            inst = context.build(self._type)
            if self._store:
                context.add(inst, as_type=self._as_type)

        return inst


def dependencies(cls):
    deps = _get_dependencies(cls)
    for name, annotation in get_type_hints(cls).items():
        if isinstance(annotation, Injectable) and not hasattr(cls, name):
            setattr(cls, name, annotation)
            deps.add(annotation)

    return cls


def _get_dependencies(cls):
    try:
        return cls.__bevy_dependencies__
    except AttributeError:
        cls.__bevy_dependencies__ = set()
        return cls.__bevy_dependencies__


class NotBoundToAContext(BaseException):
    """Raised when no Bevy context is found on an object."""