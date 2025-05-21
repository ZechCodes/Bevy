import typing as t
from inspect import get_annotations, signature

from tramp.optionals import Optional

import bevy.injections as injections
import bevy.registries as registries
from bevy.context_vars import GlobalContextMixin, get_global_container, global_container
from bevy.dependencies import DependencyMetadata
from bevy.hooks import Hook

type Instance = t.Any


def issubclass_or_raises[T](cls: T, class_or_tuple: t.Type[T] | tuple[t.Type[T], ...], exception: Exception) -> bool:
    try:
        return issubclass(cls, class_or_tuple)
    except TypeError as e:
        raise exception from e


class Container(GlobalContextMixin, var=global_container):
    """Stores instances for dependencies and provides utilities for injecting dependencies into callables at runtime.

    Containers can be branched to isolate dependencies while still sharing the same registry and preexisting instances."""
    def __init__(self, registry: "registries.Registry", *, parent: "Container | None" = None):
        super().__init__()
        self.registry = registry
        self.instances: dict[t.Type[Instance], Instance] = {}
        self._parent = parent

    def branch(self) -> "Container":
        """Creates a branch off of the current container, isolating dependencies from the parent container. Dependencies
        existing on the parent container will be shared with the branched container."""
        return Container(registry=self.registry, parent=self)

    def call[**P, R](
        self, func: "t.Callable[P, R] | injections.InjectionFunctionWrapper[P, R]", *args: P.args, **kwargs: P.kwargs
    ) -> R:
        """Calls a function or class with the provided arguments and keyword arguments, injecting dependencies from the
        container. This will create instances of any dependencies that are not already stored in the container or its
        parents."""
        match func:
            case injections.InjectionFunctionWrapper() as wrapper:
                return wrapper.call_using(self, *args, **kwargs)

            case _:
                return self._call(func, *args, **kwargs)

    @t.overload
    def get[T: Instance](self, dependency: t.Type[T]) -> T:
        ...

    @t.overload
    def get[T: Instance, D](self, dependency: t.Type[T], *, default: D) -> T | D:
        ...

    def get[T: Instance, D](self, dependency: t.Type[T], **kwargs) -> T | D:
        """Gets an instance of the desired dependency from the container. If the dependency is not already stored in the
        container or its parents, a new instance will be created and stored for reuse. When a default is given it will
        be returned instead of creating a new instance, the default is not stored."""
        using_default = False
        match self.registry.hooks[Hook.GET_INSTANCE].handle(self, dependency):
            case Optional.Some(v):
                instance = v

            case Optional.Nothing():
                if dep := self._get_existing_instance(dependency):
                    instance = dep.value
                else:
                    dep = None
                    if self._parent:
                        dep = self._parent.get(dependency, default=None)

                    if dep is None:
                        if "default" in kwargs:
                            dep = kwargs["default"]
                            using_default = True
                        else:
                            dep = self._create_instance(dependency)

                    instance = dep

            case _:
                raise ValueError(f"Invalid value for dependency: {dependency}, must be an Optional type.")

        instance = self.registry.hooks[Hook.GOT_INSTANCE].filter(self, instance)
        if not using_default:
            self.instances[dependency] = instance

        return instance

    def _call[**P, R](self, func: t.Callable[P, R] | t.Type[R], *args: P.args, **kwargs: P.kwargs) -> R:
        match func:
            case type():
                return self._call_type(func, *args, **kwargs)

            case _:
                return self._call_function(func, *args, **kwargs)

    def _call_function[**P, R](self, func: t.Callable[P, R], *args: P.args, **kwargs: P.kwargs) -> R:
        f = _unwrap_function(func)
        sig = signature(f)
        ns = getattr(f, "__globals__", {})  # If there's no __init__ method use an empty namespace
        annotations = get_annotations(f, globals=ns, eval_str=True)

        params = sig.bind_partial(*args, **kwargs)
        params.arguments |= {
            name: self.get(annotations[name]) if parameter.default.factory is None else parameter.default.factory(self)
            for name, parameter in sig.parameters.items()
            if isinstance(parameter.default, DependencyMetadata) and name not in params.arguments
        }
        return func(*params.args, **params.kwargs)

    def _call_type[T](self, type_: t.Type[T], *args, **kwargs) -> T:
        instance = type_.__new__(type_, *args, **kwargs)
        self.call(instance.__init__, *args, **kwargs)
        return instance

    def _create_instance(self, dependency: t.Type[Instance]) -> Instance:
        match self.registry.hooks[Hook.CREATE_INSTANCE].handle(self, dependency):
            case Optional.Some(v):
                instance = v

            case Optional.Nothing():
                match self._find_factory_for_type(dependency):
                    case Optional.Some(factory):
                        instance = factory(self)

                    case Optional.Nothing():
                        instance = self._handle_unsupported_dependency(dependency)

                    case _:
                        raise RuntimeError(f"Impossible state reached.")

            case _:
                raise ValueError(
                    f"Invalid value returned from hook for dependency: {dependency}, must be a {Optional.__qualname__}."
                )

        return self.registry.hooks[Hook.CREATED_INSTANCE].filter(self, instance)

    def _handle_unsupported_dependency(self, dependency):
        match self.registry.hooks[Hook.HANDLE_UNSUPPORTED_DEPENDENCY].handle(self, dependency):
            case Optional.Some(v):
                return v

            case Optional.Nothing():
                raise TypeError(f"No handler found that can handle dependency: {dependency!r}")

            case _:
                raise ValueError(
                    f"Invalid value returned from hook for dependency: {dependency}, must be a "
                    f"{Optional.__qualname__}."
                )

    def _find_factory_for_type(self, dependency):
        if not isinstance(dependency, type):
            return Optional.Nothing()

        for factory_type, factory in self.registry.factories.items():
            if issubclass_or_raises(
                dependency,
                factory_type,
                TypeError(f"Cannot check if {dependency!r} is a subclass of {factory_type!r}")
            ):
                return Optional.Some(factory)

        return Optional.Nothing()

    def _get_existing_instance(self, dependency: t.Type[Instance]) -> Optional[Instance]:
        if dependency in self.instances:
            return Optional.Some(self.instances[dependency])

        if not isinstance(dependency, type):
            return Optional.Nothing()

        for instance_type, instance in self.instances.items():
            if issubclass_or_raises(
                dependency,
                instance_type,
                TypeError(f"Cannot check if {dependency} is a subclass of {instance_type}")
            ):
                return Optional.Some(instance)

        return Optional.Nothing()


def _unwrap_function(func):
    if hasattr(func, "__wrapped__"):
        return _unwrap_function(func.__wrapped__)

    if hasattr(func, "__func__"):
        return _unwrap_function(func.__func__)

    return func


@t.overload
def get_container() -> Container:
    ...


@t.overload
def get_container(obj: Container | None) -> Container:
    ...


@t.overload
def get_container(*, using_registry: "registries.Registry") -> Container:
    ...


@t.overload
def get_container(obj: Container | None, *, using_registry: "registries.Registry") -> Container:
    ...


def get_container(*args, **kwargs) -> Container:
    """Gets a container from the global context, a provided container, or a registry.

    With no parameters it returns the global container. Note that this will create a new container if the global context
    does not already have one.

    When given a container it returns that container unless it is None. When it is None it returns the global container.
    Note that this will create a new container if the provided container is None and the global context does not already
    have one.

    A registry can be passed to use in place of the global registry with the using_registry keyword argument. Containers
    created by this registry will not be stored in the global context."""
    match args:
        case (Container() as container,):
            return container

        case () | (None,):
            match kwargs:
                case {"using_registry": registries.Registry() as registry}:
                    return registry.create_container()

                case {}:
                    return get_global_container()

                case _:
                    names = (name for name in kwargs if name not in {"using_registry"})
                    raise NameError(
                        f"Invalid keyword name(s): {', '.join(names)}"
                    )

        case _:
            raise ValueError(f"Invalid positional arguments: {args}\nExpected no parameters, a Container, or None.")
