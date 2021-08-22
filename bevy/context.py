"""The context object handles the creation of a context in which an object will be constructed.

The context should be initialized with the object that the context is being built for. It can optionally take a
parent context that it can inherit dependencies from. Once all dependencies have been configured the object can be
constructed by calling the context object's build method. This method can take any args that should be passed to the
object when it is initialized.
"""
from __future__ import annotations
from bevy.builder import Builder, is_builder
from bevy.exceptions import CanOnlyInjectIntoInjectables
from bevy.injectable import Injectable, is_injectable
from bevy.injector import Injector, is_injector
from functools import partial
from inspect import isclass
from typing import Any, Generic, Optional, Type, TypeVar, Union


T = TypeVar("T")


class Context(Generic[T]):
    def __init__(
        self,
        obj: Injectable[Type[T]],
        parent: Optional[Context[T]] = None,
        *args,
        **kwargs,
    ):
        self._args = args
        self._branches: dict[Type[T], Context[T]] = {}
        self._dependencies: dict[Type[T], T] = {Context: self}
        self._kwargs = kwargs
        self._obj = obj
        self._parent = parent

    def add(self, dependency: Any):
        """Stores an instance in the context repository."""
        self._dependencies[type(dependency)] = dependency

    def add_as(self, dependency: Any, adding_as: Union[Type[T], Injectable[Type[T]]]):
        """Stores an instance in the context repository that will be used for types of the provided type."""
        self._dependencies[adding_as] = dependency

    def branch(self, cls: Type[Injectable[T]], *args, **kwargs) -> Context[T]:
        """Creates a child context for the given injectable type."""
        self._branches[cls] = Context(cls, self, *args, **kwargs)
        return self._branches[cls]

    def build(self) -> T:
        """Builds an instance of the object that was passed to the context. This will also resolve the branches and
        add them to the repository."""
        self._resolve_branches()
        return self.construct(self._obj, *self._args, **self._kwargs)

    def construct(
        self, obj: Union[Injectable[T], Builder[T], Type[T]], *args, **kwargs
    ) -> T:
        """Creates an instance of a class. If the class is injectable it will use the bevy context class method."""
        if is_injectable(obj):
            obj = partial(obj, __bevy_context__=self)

        elif is_builder(obj):
            obj = partial(obj.__bevy_build__, self)

        if is_builder(obj):
            obj = obj.__bevy_build__

        return obj(*args, **kwargs) if callable(obj) else obj

    def get(
        self, cls: Union[Injectable[T], Injector[T], Type[T]], *args, **kwargs
    ) -> T:
        """Gets an instance associated with the requested type. If it is not found in the context's repository or
        in the repository of the parent's context an instance will be created using any provided args."""
        if dependency := self._find_dependency_match(cls):
            return dependency

        if self._parent and self._parent.has(cls):
            return self._parent.get(cls)

        dependency = self.construct(cls, *args, **kwargs)
        self.add(dependency)
        return dependency

    def has(self, cls: Type[T], check_parent: bool = True) -> bool:
        """Checks if a matching dependency exists in the context's repository or optionally in the repository of the
        parent context."""
        match = self._find_dependency_match(cls)
        if match is None and check_parent and self._parent:
            return self._parent.has(cls)

        return match is not None

    def inject(
        self,
        dependency: Union[Injectable[T], Type[T]],
        instance: Any,
        attr_name: str,
        *args,
        **kwargs,
    ):
        """Will attempt to inject the dependency into the injectable. If the instance being injected into is not an
        injectable an CanOnlyInjectIntoInjectables exception will be raised. If the dependency supports the injector
        protocol it will use the dependency's inject method, otherwise the context will get an instance of the
        dependency and set it as an attribute."""
        if not is_injectable(instance):
            raise CanOnlyInjectIntoInjectables(
                f"Attempted to inject into {instance}, it is not an instance of {Injectable}"
            )

        if is_injector(dependency):
            inject = dependency.__bevy_inject__
            if isinstance(dependency, type) and (
                not hasattr(inject, "__self__") or not isinstance(inject.__self__, type)
            ):
                inject = self.get(dependency).__bevy_inject__
            inject(instance, attr_name, self, *args, **kwargs)
        else:
            setattr(instance, attr_name, self.get(dependency, *args, **kwargs))

    def _find_dependency_match(self, obj: Any) -> Optional[T]:
        def subclass_check(dt, o):
            cls: Type[T] = o if isclass(o) else type(o)
            return issubclass(cls, dt) or issubclass(dt, cls)

        for dependency_obj, dependency in self._dependencies.items():
            is_match = getattr(
                dependency,
                "__bevy_is_match__",
                partial(subclass_check, dependency_obj),
            )
            if is_match(obj):
                return dependency

        return

    def _resolve_branches(self):
        for cls, branch in self._branches.items():
            self.add_as(branch.build(), cls)
