from typing import Callable, TypeVar, ParamSpec, TypeAlias, get_type_hints
from functools import wraps
from inspect import signature
from bevy.dependency_descriptor import Dependency
from bevy.repository import get_repository

_P = ParamSpec("_P")
_R = TypeVar("_R")
_C: TypeAlias = Callable[_P, _R]


def inject(func: _C) -> Callable[_P, _R]:
    sig = signature(func)
    type_hints = get_type_hints(func)
    inject_parameters = {
        name: type_hints[name]
        for name, parameter in sig.parameters.items()
        if isinstance(parameter.default, Dependency)
    }

    @wraps(func)
    def injector(*args: _P.args, **kwargs: _P.kwargs) -> _R:
        params = sig.bind_partial(*args, **kwargs)
        repo = get_repository()
        params.arguments |= {
            name: repo.get(dependency_type)
            for name, dependency_type in inject_parameters.items()
            if name not in params.arguments
        }
        return func(*params.args, **params.kwargs)

    return injector
