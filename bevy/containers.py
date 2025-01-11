import typing as t
from inspect import get_annotations, signature

from tramp.optionals import Optional

from bevy.context_vars import ContextVarContextManager, get_global_container, global_container
from bevy.dependencies import Dependency
import bevy.registries as registries

from bevy.hooks import Hook
from bevy.injections import InjectionFunctionWrapper

type Instance = t.Any


class Container(ContextVarContextManager, var=global_container):
    def __init__(self, registry: "registries.Registry", *, parent: "Container | None" = None):
        super().__init__()
        self.registry = registry
        self.instances: dict[t.Type[Instance], Instance] = {}
        self._parent = parent

    def branch(self) -> "Container":
        return Container(registry=self.registry, parent=self)

    def call[**P, R](
        self, func: t.Callable[P, R] | InjectionFunctionWrapper[P, R], *args: P.args, **kwargs: P.kwargs
    ) -> R:
        match func:
            case InjectionFunctionWrapper() as wrapper:
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

        instance = self.registry.hooks[Hook.GOT_INSTANCE].filter(self, instance)
        if not using_default:
            self.instances[dependency] = instance

        return instance

    def _call[**P, R](self, func: t.Callable[P, R] | t.Type[R], *args: P.args, **kwargs: P.kwargs) -> R:
        if isinstance(func, type):
            instance = func.__new__(func, *args, **kwargs)
            self.call(instance.__init__, *args, **kwargs)
            return instance

        f = _unwrap_function(func)
        sig = signature(f)
        ns = f.__globals__
        annotations = get_annotations(f, globals=ns, eval_str=True)

        params = sig.bind_partial(*args, **kwargs)
        params.arguments |= {
            name: self.get(annotations[name]) if parameter.default.factory is None else parameter.default.factory(self)
            for name, parameter in sig.parameters.items()
            if isinstance(parameter.default, Dependency) and name not in params.arguments
        }
        return func(*params.args, **params.kwargs)

    def _create_instance(self, dependency: t.Type[Instance]) -> Instance:
        match self.registry.hooks[Hook.CREATE_INSTANCE].handle(self, dependency):
            case Optional.Some(v):
                instance = v

            case Optional.Nothing():
                for factory_type, factory in self.registry.factories.items():
                    if issubclass(dependency, factory_type):
                        instance = factory(self)
                        break

                else:
                    match self.registry.hooks[Hook.HANDLE_UNSUPPORTED_DEPENDENCY].handle(self, dependency):
                        case Optional.Some(v):
                            instance = v

                        case Optional.Nothing():
                            raise TypeError(f"No value found for {dependency}")

        return self.registry.hooks[Hook.CREATED_INSTANCE].filter(self, instance)

    def _get_existing_instance(self, dependency: t.Type[Instance]) -> Optional[Instance]:
        for instance_type, instance in self.instances.items():
            if issubclass(dependency, instance_type):
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
def get_container(obj: "Container | registries.Registry") -> Container:
    ...


def get_container(*args) -> Container:
    match args:
        case (Container() as container):
            return container

        case (registries.Registry() as registry):
            return registry.create_container()

        case ():
            if container := get_global_container():
                return container
            else:
                return registries.get_registry().create_container()

        case _:
            raise ValueError(f"Invalid args: {args}\nExpected either a Container, Registry, or no parameters.")
