"""
Dependency injection decorator system with type-safe annotations.

This module provides the @injectable and @auto_inject decorators for 
configuring and enabling dependency injection on functions using the
Inject[T] type annotation system.

Example:
    Basic usage with container:
    
    >>> from bevy import injectable, Inject, Container, Registry
    >>> 
    >>> @injectable
    >>> def process_data(service: Inject[UserService], data: str):
    ...     return service.process(data)
    >>> 
    >>> container = Container(Registry())
    >>> result = container.call(process_data, data="test")
    
    Global container with auto_inject:
    
    >>> from bevy import auto_inject, injectable, Inject
    >>> 
    >>> @auto_inject
    >>> @injectable
    >>> def process_data(service: Inject[UserService], data: str):
    ...     return service.process(data)
    >>> 
    >>> result = process_data(data="test")  # Uses global container
"""

import inspect
import time
from dataclasses import dataclass, field
from functools import update_wrapper
from typing import Any, Callable, Dict, get_type_hints, Optional, Tuple

from bevy.injection_types import (extract_injection_info, InjectionStrategy, Options, TypeMatchingStrategy)


def analyze_function_signature(
    func, 
    strategy: InjectionStrategy, 
    params: Optional[list[str]] = None
) -> Dict[str, Tuple[type, Optional[Options]]]:
    """
    Analyze function signature to determine which parameters should be injected.
    
    Args:
        func: Function to analyze
        strategy: Strategy for determining injectable parameters
        params: List of parameter names (used with ONLY strategy)
        
    Returns:
        Dictionary mapping parameter names to (type, options) tuples
    """
    sig = inspect.signature(func)
    type_hints = get_type_hints(func, include_extras=True)
    injection_params = {}
    
    for param_name, param in sig.parameters.items():
        # Skip *args and **kwargs
        if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
            continue
            
        # Get type annotation
        annotation = type_hints.get(param_name, param.annotation)
        if annotation == inspect.Parameter.empty:
            continue
            
        # Extract injection info
        actual_type, options = extract_injection_info(annotation)
        
        # Determine if this parameter should be injected
        # For REQUESTED_ONLY, we need to know if the original annotation was Inject[]
        is_inject_annotation = (actual_type != annotation)
        should_inject = _should_inject_parameter(
            param_name, actual_type, options, strategy, params, is_inject_annotation
        )
        
        if should_inject:
            injection_params[param_name] = (actual_type, options)
    
    return injection_params


def _should_inject_parameter(
    param_name: str,
    actual_type: type,
    options: Optional[Options],
    strategy: InjectionStrategy,
    params: Optional[list[str]],
    is_inject_annotation: bool = False
) -> bool:
    """
    Determine if a parameter should be injected based on strategy.
    
    Args:
        param_name: Name of the parameter
        actual_type: The parameter's type
        options: Injection options (None if not using Inject[])
        strategy: Injection strategy
        params: List of parameter names (for ONLY strategy)
        
    Returns:
        True if parameter should be injected
    """
    if strategy == InjectionStrategy.REQUESTED_ONLY:
        # Only inject if parameter uses Inject[] syntax
        return is_inject_annotation
    
    elif strategy == InjectionStrategy.ANY_NOT_PASSED:
        # Inject any parameter with type annotation
        return actual_type != inspect.Parameter.empty
    
    elif strategy == InjectionStrategy.ONLY:
        # Inject only parameters in the specified list
        return params is not None and param_name in params

    return False


@dataclass
class _InjectableConfig:
    """Shared configuration for an injectable callable."""

    strategy: InjectionStrategy
    params: Optional[list[str]]
    strict: bool
    type_matching: TypeMatchingStrategy
    debug: bool
    cache_analysis: bool
    auto_inject: bool = False
    analysis_cache: Dict[Callable[..., Any], Dict[str, Tuple[type, Optional[Options]]]] = field(default_factory=dict)


class InjectableCallable:
    """Wrapper that performs dependency injection against a container."""

    __slots__ = ("_func", "_config", "__wrapped__", "__dict__")

    def __init__(self, func: Callable[..., Any], config: _InjectableConfig):
        self._func = func
        self._config = config
        update_wrapper(self, func)
        self.__wrapped__ = func

    # ------------------------------------------------------------------
    # Descriptor behaviour ------------------------------------------------
    def __get__(self, instance, owner):
        descriptor_get = getattr(self._func, "__get__", None)
        if descriptor_get is None:
            return self

        bound = descriptor_get(instance, owner)
        if bound is self._func and instance is None:
            return self

        return type(self)(bound, self._config)

    def _analyze(self, target_func: Callable[..., Any]) -> Dict[str, Tuple[type, Optional[Options]]]:
        if self._config.cache_analysis and target_func in self._config.analysis_cache:
            return self._config.analysis_cache[target_func]

        params = analyze_function_signature(target_func, self._config.strategy, self._config.params)
        if self._config.cache_analysis:
            self._config.analysis_cache[target_func] = params
        return params

    def _build_injection_configuration(self) -> Dict[str, Any]:
        params = self._analyze(self._func)
        return {
            "params": params,
            "strategy": self._config.strategy,
            "type_matching": self._config.type_matching,
            "strict_mode": self._config.strict,
            "debug_mode": self._config.debug,
        }

    # ------------------------------------------------------------------
    # Call handling ------------------------------------------------------
    def call_using(self, container, /, *args, **kwargs):
        from bevy.containers import Container  # Local import to avoid cycle

        if not isinstance(container, Container):  # pragma: no cover - defensive
            raise TypeError("container must be a Container instance")

        start_time = time.time()
        function_name = getattr(self._func, "__name__", str(self._func))
        current_injection_chain = container._build_injection_chain(function_name)
        injection_config = self._build_injection_configuration()

        sig = inspect.signature(self._func)
        bound_args = sig.bind_partial(*args, **kwargs)
        bound_args.apply_defaults()

        injected_params = self._inject_missing_dependencies(
            container,
            injection_config,
            bound_args,
            function_name,
            current_injection_chain,
        )

        result = self._func(*bound_args.args, **bound_args.kwargs)
        container._call_post_injection_hook(
            function_name,
            injected_params,
            result,
            injection_config["strategy"],
            injection_config["debug_mode"],
            start_time,
        )

        return result

    def __call__(self, *args, **kwargs):
        if self.auto_inject:
            from bevy.context_vars import get_global_container

            container = get_global_container()
            return self.call_using(container, *args, **kwargs)

        return self._func(*args, **kwargs)

    # ------------------------------------------------------------------
    # Injection helpers --------------------------------------------------
    def _inject_missing_dependencies(
        self,
        container,
        injection_config: Dict[str, Any],
        bound_args,
        function_name: str,
        current_injection_chain: list[str],
    ) -> Dict[str, Any]:
        from bevy.injection_types import DependencyResolutionError

        injected_params: Dict[str, Any] = {}

        for param_name, (param_type, options) in injection_config["params"].items():
            should_inject = (
                param_name not in bound_args.arguments
                or injection_config["strategy"] == InjectionStrategy.REQUESTED_ONLY
            )

            if not should_inject:
                continue

            try:
                injected_value = container._inject_single_dependency(
                    param_name,
                    param_type,
                    options,
                    injection_config,
                    function_name,
                    current_injection_chain,
                )
                bound_args.arguments[param_name] = injected_value
                injected_params[param_name] = injected_value
            except DependencyResolutionError:
                if param_name not in bound_args.arguments:
                    raise

        return injected_params

    # ------------------------------------------------------------------
    # Introspection ------------------------------------------------------
    def injection_metadata(self) -> Dict[str, Any]:
        return {
            "params": self._analyze(self._func),
            "strategy": self._config.strategy,
            "type_matching": self._config.type_matching,
            "strict_mode": self._config.strict,
            "debug_mode": self._config.debug,
            "cache_analysis": self._config.cache_analysis,
        }

    # ------------------------------------------------------------------
    # Properties ---------------------------------------------------------
    @property
    def auto_inject(self) -> bool:
        return self._config.auto_inject

    @auto_inject.setter
    def auto_inject(self, value: bool) -> None:
        self._config.auto_inject = value

    # ------------------------------------------------------------------
    # Constructors -------------------------------------------------------
    @classmethod
    def from_callable(
        cls,
        func: Callable[..., Any],
        *,
        strategy: InjectionStrategy | None = None,
        params: Optional[list[str]] = None,
        strict: bool = True,
        type_matching: TypeMatchingStrategy | None = None,
        debug: bool = False,
        cache_analysis: bool = True,
    ) -> "InjectableCallable":
        if isinstance(func, cls):
            return func

        actual_strategy = strategy or InjectionStrategy.ANY_NOT_PASSED
        if actual_strategy == InjectionStrategy.DEFAULT:
            actual_strategy = InjectionStrategy.REQUESTED_ONLY

        actual_type_matching = type_matching or TypeMatchingStrategy.SUBCLASS
        if actual_type_matching == TypeMatchingStrategy.DEFAULT:
            actual_type_matching = TypeMatchingStrategy.SUBCLASS

        config = _InjectableConfig(
            strategy=actual_strategy,
            params=list(params) if params is not None else None,
            strict=strict,
            type_matching=actual_type_matching,
            debug=debug,
            cache_analysis=cache_analysis,
        )
        return cls(func, config)


def _locate_injectable(func) -> Optional[InjectableCallable]:
    """Traverse wrappers to find an InjectableCallable instance."""

    current = func
    visited: set[int] = set()
    while current is not None and id(current) not in visited:
        visited.add(id(current))
        if isinstance(current, InjectableCallable):
            return current
        current = getattr(current, "__wrapped__", None)

    return None


def injectable(
    func=None,
    *,
    strategy: InjectionStrategy = InjectionStrategy.DEFAULT,
    params: Optional[list[str]] = None,
    strict: bool = True,
    type_matching: TypeMatchingStrategy = TypeMatchingStrategy.DEFAULT,
    debug: bool = False,
    cache_analysis: bool = True
):
    """
    Configure dependency injection for a function.
    
    This decorator analyzes the function signature and stores injection metadata
    but does not change the function's runtime behavior. Use @auto_inject to
    enable automatic injection using the global container, or call the function
    via Container.call().
    
    Args:
        strategy: Controls which parameters are injected (default: REQUESTED_ONLY)
        params: List of parameter names to inject (used with ONLY strategy)
        strict: Whether to raise errors for missing dependencies (default: True)
        type_matching: How to match types during resolution (default: SUBCLASS)
        debug: Enable debug logging during injection (default: False)
        cache_analysis: Cache function signature analysis for performance (default: True)
    
    Example:
        Basic usage:
        
        >>> @injectable
        >>> def process_data(service: Inject[UserService], data: str):
        ...     return service.process(data)
        
        With configuration:
        
        >>> @injectable(strategy=InjectionStrategy.ANY_NOT_PASSED, debug=True)
        >>> def auto_inject_all(service: UserService, db: Database, data: str):
        ...     return f"Processed {data} with {service} and {db}"
        
        Selective injection:
        
        >>> @injectable(strategy=InjectionStrategy.ONLY, params=["service"])
        >>> def selective(service: UserService, manual: str):
        ...     return f"{service} processed {manual}"
    
    Returns:
        The decorated function with injection metadata attached.
    """
    # Convert DEFAULT enums to actual strategies
    actual_strategy = (
        InjectionStrategy.REQUESTED_ONLY 
        if strategy == InjectionStrategy.DEFAULT 
        else strategy
    )
    actual_type_matching = (
        TypeMatchingStrategy.SUBCLASS 
        if type_matching == TypeMatchingStrategy.DEFAULT 
        else type_matching
    )
    
    def decorator(target_func):
        config = _InjectableConfig(
            strategy=actual_strategy,
            params=list(params) if params is not None else None,
            strict=strict,
            type_matching=actual_type_matching,
            debug=debug,
            cache_analysis=cache_analysis,
        )

        return InjectableCallable(target_func, config)

    # Handle both @injectable and @injectable() usage
    if func is None:
        # Called with arguments: @injectable(strategy=...)
        return decorator
    else:
        # Called without arguments: @injectable
        return decorator(func)


def auto_inject(func):
    """Enable automatic injection using the global container.

    The decorator searches through the ``__wrapped__`` chain for an existing
    :class:`InjectableCallable`. If one is found, the auto-inject flag is set on
    that wrapper. Otherwise the target is wrapped in a new ``InjectableCallable``
    using the :class:`InjectionStrategy.REQUESTED_ONLY` strategy.

    Direct invocations call ``call_using`` with the global container, while
    :meth:`bevy.containers.Container.call` will still inject using the container
    it was invoked on. If additional decorators wrap the result *after*
    ``@auto_inject``, they will hide the injectable wrapper from
    ``Container.call``; in that scenario the wrapper is injected with the calling
    container while the inner auto-injected callable uses the global container.
    This double-injection is the intended behaviour and is documented for users.
    """

    injectable_callable = _locate_injectable(func)
    if injectable_callable is None:
        injectable_callable = InjectableCallable.from_callable(
            func,
            strategy=InjectionStrategy.REQUESTED_ONLY,
            cache_analysis=True,
        )
        func = injectable_callable

    injectable_callable.auto_inject = True
    return func


def get_injection_info(func) -> Optional[Dict[str, Any]]:
    """
    Get injection metadata from a function.
    
    Args:
        func: Function to get metadata from
        
    Returns:
        Dictionary with injection metadata or None if not injectable
    """
    injectable_callable = _locate_injectable(func)
    if injectable_callable is None:
        return None

    return injectable_callable.injection_metadata()


def is_injectable(func) -> bool:
    """
    Check if a function has been configured for injection.
    
    Args:
        func: Function to check
        
    Returns:
        True if function has injection metadata
    """
    return _locate_injectable(func) is not None
