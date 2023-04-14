from typing import Any, Callable, TypeVar, ParamSpec, TypeAlias
from functools import wraps
from inspect import signature, get_annotations
from bevy.dependency_descriptor import Dependency
from bevy.repository import get_repository

_P = ParamSpec("_P")
_R = TypeVar("_R")
_C: TypeAlias = Callable[_P, _R]


def inject(func: _C) -> Callable[_P, _R]:
    sig = signature(func)
    ns = _get_function_namespace(func)
    annotations = get_annotations(func, globals=ns, eval_str=True)
    inject_parameters = {
        name: annotations[name]
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


def _get_function_namespace(func: _C) -> dict[str, Any]:
    return _unwrap_function(func).__globals__


def _unwrap_function(func: _C) -> _C:
    if hasattr(func, "__func__"):
        return _unwrap_function(func.__func__)

    return func
