"""The constructor object handles the creation of a context in which an object will be constructed.

The constructor should be initialized with the object that the context is being built for. It can optionally take a
parent constructor that it can inherit dependencies from. Once all dependencies have been configured the object can be
constructed by calling the constructor object's build method. This method can take any args that should be passed to the
object when it is initialized.
"""
from __future__ import annotations
from bevy.exceptions import CanOnlyInjectIntoInjectables
from bevy.injectable import Injectable, is_injectable
from bevy.injector import Injector, is_injector
from inspect import isclass
from typing import Any, Generic, Optional, Type, TypeVar, Union


T = TypeVar("T")


class Constructor(Generic[T]):
    def __init__(
        self,
        obj: Type[Injectable[T]],
        parent: Optional[Constructor[T]] = None,
        *args,
        **kwargs,
    ):
        self._args = args
        self._branches: dict[Type[T], Constructor[T]] = {}
        self._dependencies: dict[Type[T], T] = {Constructor: self}
        self._kwargs = kwargs
        self._obj = obj
        self._parent = parent

    def add(self, dependency: Any):
        """Stores an instance in the constructor repository."""
        self._dependencies[type(dependency)] = dependency

    def add_as(self, dependency: Any, adding_as: Type[T]):
        """Stores an instance in the constructor repository that will be used for types of the provided type."""
        self._dependencies[adding_as] = dependency

    def branch(self, cls: Type[Injectable[T]], *args, **kwargs) -> Constructor[T]:
        """Creates a child constructor for the given injectable type."""
        self._branches[cls] = Constructor(cls, self, *args, **kwargs)
        return self._branches[cls]

    def build(self) -> T:
        """Builds an instance of the object that was passed to the constructor. This will also resolve the branches and
        add them to the repository."""
        self._resolve_branches()
        return self.construct(self._obj, *self._args, **self._kwargs)

    def construct(self, obj: Union[Injectable[T], Type[T]], *args, **kwargs) -> T:
        """Creates an instance of a class. If the class is injectable it will use the bevy constructor class method."""
        if is_injectable(obj):
            kwargs["bevy_constructor"] = self

        return obj(*args, **kwargs) if callable(obj) else obj

    def get(self, cls: Union[Injectable[T], Type[T]], *args, **kwargs) -> T:
        """Gets an instance associated with the requested type. If it is not found in the constructor's repository or
        in the repository of the parent's constructor an instance will be created using any provided args."""
        if dependency := self._find_dependency_match(cls):
            return dependency

        if self._parent and self._parent.has(cls):
            return self._parent.get(cls)

        dependency = self.construct(cls, *args, **kwargs)
        self.add(dependency)
        return dependency

    def has(self, cls: Type[T], check_parent: bool = True) -> bool:
        """Checks if a matching dependency exists in the constructor's repository or optionally in the repository of the
        parent constructor."""
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
        protocol it will use the dependency's inject method, otherwise the constructor will get an instance of the
        dependency and set it as an attribute."""
        if not is_injectable(instance):
            raise CanOnlyInjectIntoInjectables(
                f"Attempted to inject into {instance}, it is not an instance of {Injectable}"
            )

        if is_injector(dependency):
            inject = dependency.__bevy_inject__
            if not hasattr(inject, "__self__") or type(inject.__self__) is not type:
                inject = self.get(dependency).__bevy_inject__
            inject(instance, attr_name, self, *args, **kwargs)
        else:
            setattr(instance, attr_name, self.get(dependency, *args, **kwargs))

    def _find_dependency_match(self, cls: Union[Type[T], T]) -> Optional[T]:
        if not isclass(cls):
            cls: Type[T] = type(cls)

        for dependency_type, dependency in self._dependencies.items():
            if issubclass(cls, dependency_type) or issubclass(dependency_type, cls):
                return dependency

        return

    def _resolve_branches(self):
        for cls, branch in self._branches.items():
            self.add_as(branch.build(), cls)
