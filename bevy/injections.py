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
from functools import wraps
from typing import get_type_hints, Optional, Any, Dict, Tuple

from bevy.injection_types import (
    InjectionStrategy, TypeMatchingStrategy, Options,
    extract_injection_info, is_optional_type, get_non_none_type
)


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
        # Analyze function signature and store metadata
        if cache_analysis and hasattr(target_func, '_bevy_injection_params'):
            # Use cached analysis if available
            injection_params = target_func._bevy_injection_params
        else:
            injection_params = analyze_function_signature(target_func, actual_strategy, params)
            
        # Store all configuration on function
        target_func._bevy_injection_params = injection_params
        target_func._bevy_injection_strategy = actual_strategy
        target_func._bevy_type_matching = actual_type_matching
        target_func._bevy_strict_mode = strict
        target_func._bevy_debug_mode = debug
        target_func._bevy_cache_analysis = cache_analysis
        
        return target_func

    # Handle both @injectable and @injectable() usage
    if func is None:
        # Called with arguments: @injectable(strategy=...)
        return decorator
    else:
        # Called without arguments: @injectable
        return decorator(func)


def auto_inject(func):
    """
    Enable automatic injection using the global container.
    
    This decorator wraps the function to automatically inject dependencies
    from the global container when the function is called. The function must
    be decorated with @injectable first.
    
    **Important:** @auto_inject must come before @injectable in the decorator chain.
    
    Args:
        func: Function to enable auto-injection for
        
    Returns:
        Wrapped function that performs automatic injection
        
    Raises:
        ValueError: If function is not decorated with @injectable
    
    Example:
        >>> @auto_inject
        >>> @injectable
        >>> def process_data(service: Inject[UserService], data: str):
        ...     return service.process(data)
        >>> 
        >>> # Can now call directly without container
        >>> result = process_data(data="test")
        
        Error case (wrong decorator order):
        
        >>> @injectable
        >>> @auto_inject  # Wrong order!
        >>> def bad_function(service: Inject[UserService]):
        ...     pass  # Raises ValueError
    """
    if not hasattr(func, '_bevy_injection_params'):
        raise ValueError(
            f"Function {func.__name__} must be decorated with @injectable first. "
            f"Use @injectable before @auto_inject."
        )
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Import here to avoid circular imports
        from bevy.context_vars import get_global_container
        
        container = get_global_container()
        return container.call(func, *args, **kwargs)
    
    # Preserve injection metadata
    wrapper._bevy_injection_params = func._bevy_injection_params
    wrapper._bevy_injection_strategy = func._bevy_injection_strategy
    wrapper._bevy_type_matching = func._bevy_type_matching
    wrapper._bevy_strict_mode = func._bevy_strict_mode
    wrapper._bevy_debug_mode = func._bevy_debug_mode
    wrapper._bevy_cache_analysis = func._bevy_cache_analysis
    
    return wrapper


def get_injection_info(func) -> Optional[Dict[str, Any]]:
    """
    Get injection metadata from a function.
    
    Args:
        func: Function to get metadata from
        
    Returns:
        Dictionary with injection metadata or None if not injectable
    """
    if not hasattr(func, '_bevy_injection_params'):
        return None
        
    return {
        'params': func._bevy_injection_params,
        'strategy': func._bevy_injection_strategy,
        'type_matching': func._bevy_type_matching,
        'strict_mode': func._bevy_strict_mode,
        'debug_mode': func._bevy_debug_mode,
        'cache_analysis': func._bevy_cache_analysis
    }


def is_injectable(func) -> bool:
    """
    Check if a function has been configured for injection.
    
    Args:
        func: Function to check
        
    Returns:
        True if function has injection metadata
    """
    return hasattr(func, '_bevy_injection_params')