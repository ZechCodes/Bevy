from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Callable, Generic, Type, TypeVar

import bevy.base_context as b
from bevy.sentinel import sentinel


T = TypeVar("T")
_T = TypeVar("_T")
Builder = Callable[[Type[_T], ...], _T]


NOTSET = sentinel("NOTSET")


class ProviderHasNoBoundContext(Exception):
    ...


class Provider(Generic[T], ABC):
    def __init__(self, type_: Type[T], context: b.BaseContext | None = None):
        self._context = context
        self._type = type_

    @abstractmethod
    def bind_to(self, context: b.BaseContext) -> Provider[T]:
        ...

    def create(self, type_: Type[T], *args, **kwargs) -> T:
        if not self._context:
            raise ProviderHasNoBoundContext(
                f"{self} cannot create an instance of {type_} as the provider is not bound to a context."
            )

        return self._create_instance(*args, **kwargs)

    def _create_instance(self, *args, **kwargs) -> T:
        return self._type(*args, **kwargs)

    @abstractmethod
    def get_instance(self, *args, **kwargs) -> T:
        ...

    def is_matching_provider_type(self, provider_type: Type[Provider]) -> bool:
        cls = type(self)
        return (
            provider_type is cls
            or issubclass(provider_type, cls)
            or issubclass(cls, provider_type)
        )

    def is_matching_type(self, type_: Type) -> bool:
        try:
            return (
                type_ is self._type
                or issubclass(type_, self._type)
                or issubclass(self._type, type_)
            )
        except TypeError:
            return False

    def __eq__(self, other):
        return other.is_matching_provider_type(type(self)) and other.is_matching_type(
            self._type
        )


class SharedInstanceProvider(Provider):
    def __init__(
        self,
        type_: Type[T],
        context: b.BaseContext | None = None,
        *,
        use: T | NOTSET = NOTSET,
    ):
        super().__init__(type_, context)
        self._instance = use

        if self._instance is NOTSET:
            self.get_instance = self._create_new_instance

    def _get_existing_instance(self) -> T:
        return self._instance

    def _create_new_instance(self, *args, **kwargs) -> T:
        self._instance = self.create(self._type, *args, **kwargs)
        self.get_instance = self._get_existing_instance
        return self._get_existing_instance()

    def _create_instance(self, *args, **kwargs) -> T:
        def bevy_init(s):
            s.__bevy__ = self._context

        t = type(
            self._type.__name__,
            (self._type,),
            {"__bevy_init__": bevy_init},
        )
        return t(*args, **kwargs)

    get_instance = _get_existing_instance

    def bind_to(self, context: b.BaseContext) -> Provider[T]:
        return type(self)(self._type, context, use=self._instance)

    def __repr__(self):
        return f"{type(self).__name__}<{self._type!r}, bound={bool(self._context)}, use={self._instance}>"
