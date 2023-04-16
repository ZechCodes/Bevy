from functools import wraps
from inspect import signature, get_annotations
from typing import Any, Callable, TypeVar, ParamSpec, TypeAlias

from bevy.injectors.classes import Dependency
from bevy.repository import get_repository

_P = ParamSpec("_P")
_R = TypeVar("_R")
_C: TypeAlias = Callable[_P, _R]


def inject(func: _C) -> Callable[_P, _R]:
    """This decorator creates a wrapper function that scans the decorated function for dependencies. When the function
    is later called any dependency parameters that weren't passed in will be injected by the wrapper function. This can
    intelligently handle positional only arguments, positional arguments, named arguments, and keyword only arguments.

    All parameters that should be injected need to be given a type hint that is supported by a provider and must have a
    default value that is an instance of `bevy.injectors.classes.Dependency`.
    """
    sig = signature(func)
    ns = _get_function_namespace(func)
    annotations = get_annotations(func, globals=ns, eval_str=True)
    # Determine which parameters have a declared dependency
    inject_parameters = {
        name: annotations[name]
        for name, parameter in sig.parameters.items()
        if isinstance(parameter.default, Dependency)
    }

    @wraps(func)
    def injector(*args: _P.args, **kwargs: _P.kwargs) -> _R:
        params = sig.bind_partial(*args, **kwargs)
        repo = get_repository()
        # Get instances from the repo to fill all missing dependency parameters
        params.arguments |= {
            name: repo.get(dependency_type)
            for name, dependency_type in inject_parameters.items()
            if name not in params.arguments
        }
        return func(*params.args, **params.kwargs)

    return injector


def _get_function_namespace(func: _C) -> dict[str, Any]:
    """Get the variables that the function had in its name space."""
    return _unwrap_function(func).__globals__


def _unwrap_function(func: _C) -> _C:
    """Attempt to unwrap a function from all decorators."""
    if hasattr(func, "__func__"):
        return _unwrap_function(func.__func__)

    if hasattr(func, "__wrapped__"):
        return _unwrap_function(func.__wrapped__)

    return func
