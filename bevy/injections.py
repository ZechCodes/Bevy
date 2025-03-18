import inspect
import typing as t
from functools import update_wrapper

import bevy.containers as containers


class _DescriptorProtocol(t.Protocol):
    def __get__(self, instance, owner) -> t.Callable:
        ...

    def __set__(self, instance, value):
        ...


class InjectionFunctionWrapper[**P, R]:
    """Wraps a callable to allow for injection of dependencies when called using a container. Called directly this uses
    the global container. A different container can be used with the `call_using` method."""
    def __init__(self, func: t.Callable[P, R]):
        self._func = func
        update_wrapper(self, func)

    @inspect.markcoroutinefunction
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> R:
        return self.call_using(containers.get_container(), *args, **kwargs)

    def __get__(self, instance, owner):
        return InjectionFunctionWrapper(t.cast(_DescriptorProtocol, self._func).__get__(instance, owner))

    def call_using(self, container: "containers.Container", *args: P.args, **kwargs: P.kwargs) -> R:
        """Calls the wrapped function using the provided container for dependency injection."""
        return container.call(self._func, *args, **kwargs)


def inject[**P, R](func: t.Callable[P, R]) -> InjectionFunctionWrapper[P, R]:
    """Simple wrapper around InjectionFunctionWrapper to make it cleaner to use."""
    return InjectionFunctionWrapper(func)
