"""
New container call implementation that works with the new injection system.
"""

import inspect
from typing import get_type_hints, get_origin, get_args

from bevy.injection_types import (
    InjectionStrategy, TypeMatchingStrategy, 
    extract_injection_info, is_optional_type, get_non_none_type
)
from bevy.injections import get_injection_info, analyze_function_signature


def new_call_function(container, func, args, kwargs):
    """
    New implementation of container function calling with new injection system.
    
    Args:
        container: Container instance
        func: Function to call with injection
        args: Positional arguments passed to function
        kwargs: Keyword arguments passed to function
        
    Returns:
        Result of function call with injected dependencies
    """
    # Get function signature 
    sig = inspect.signature(func)
    
    # Check if function has injection metadata from @injectable decorator
    injection_info = get_injection_info(func)
    
    if injection_info:
        # Use metadata from @injectable decorator
        injection_params = injection_info['params']
        type_matching = injection_info['type_matching']
        strict_mode = injection_info['strict_mode']
        debug_mode = injection_info['debug_mode']
    else:
        # Analyze function dynamically using ANY_NOT_PASSED strategy
        injection_params = analyze_function_signature(func, InjectionStrategy.ANY_NOT_PASSED)
        type_matching = TypeMatchingStrategy.SUBCLASS
        strict_mode = True
        debug_mode = False
    
    # Bind provided arguments
    bound_args = sig.bind_partial(*args, **kwargs)
    bound_args.apply_defaults()
    
    # Inject missing dependencies
    for param_name, (param_type, options) in injection_params.items():
        if param_name not in bound_args.arguments:
            # This parameter needs injection
            try:
                injected_value = _resolve_dependency(
                    container, param_type, options, type_matching, strict_mode, debug_mode
                )
                bound_args.arguments[param_name] = injected_value
                
                if debug_mode:
                    print(f"[BEVY DEBUG] Injected {param_name}: {param_type} = {injected_value}")
                    
            except Exception as e:
                if strict_mode:
                    # Check if this is an optional type
                    if is_optional_type(param_type):
                        bound_args.arguments[param_name] = None
                        if debug_mode:
                            print(f"[BEVY DEBUG] Optional dependency {param_name} not found, using None")
                    else:
                        raise
                else:
                    # Non-strict mode: inject None for missing dependencies
                    bound_args.arguments[param_name] = None
                    if debug_mode:
                        print(f"[BEVY DEBUG] Non-strict mode: {param_name} not found, using None")
    
    # Call function with resolved arguments
    return func(*bound_args.args, **bound_args.kwargs)


def _resolve_dependency(container, param_type, options, type_matching, strict_mode, debug_mode):
    """
    Resolve a single dependency from the container.
    
    Args:
        container: Container instance
        param_type: Type to resolve
        options: Options object with qualifier, etc.
        type_matching: Type matching strategy
        strict_mode: Whether to raise errors or return None
        debug_mode: Whether to log debug info
        
    Returns:
        Resolved dependency instance
        
    Raises:
        Exception if dependency cannot be resolved and strict_mode is True
    """
    # Handle optional types (Type | None)
    if is_optional_type(param_type):
        actual_type = get_non_none_type(param_type)
        try:
            return _resolve_single_type(container, actual_type, options, type_matching, debug_mode)
        except Exception:
            # Optional dependency not found
            return None
    else:
        return _resolve_single_type(container, param_type, options, type_matching, debug_mode)


def _resolve_single_type(container, param_type, options, type_matching, debug_mode):
    """
    Resolve a single non-optional type from the container.
    
    Args:
        container: Container instance  
        param_type: Type to resolve
        options: Options object
        type_matching: Type matching strategy
        debug_mode: Whether to log debug info
        
    Returns:
        Resolved instance
        
    Raises:
        Exception if type cannot be resolved
    """
    if debug_mode:
        print(f"[BEVY DEBUG] Resolving {param_type} with options {options}")
    
    # Handle qualified dependencies
    if options and options.qualifier:
        return _resolve_qualified_dependency(container, param_type, options.qualifier, debug_mode)
    
    # Handle configuration binding
    if options and options.from_config:
        return _resolve_from_config(container, param_type, options.from_config, debug_mode)
    
    # Handle default factory
    if options and options.default_factory:
        try:
            return container.get(param_type)
        except Exception:
            if debug_mode:
                print(f"[BEVY DEBUG] Using default factory for {param_type}")
            return options.default_factory()
    
    # Standard resolution using container.get()
    return container.get(param_type)


def _resolve_qualified_dependency(container, param_type, qualifier, debug_mode):
    """
    Resolve a qualified dependency.
    
    TODO: This will need to be implemented when qualifier support is added to Container.
    For now, raise an informative error.
    """
    raise NotImplementedError(
        f"Qualified dependencies not yet implemented. "
        f"Cannot resolve {param_type} with qualifier '{qualifier}'. "
        f"This feature will be added in a future update."
    )


def _resolve_from_config(container, param_type, config_key, debug_mode):
    """
    Resolve a dependency from configuration.
    
    TODO: This will need to be implemented when config binding is added.
    For now, raise an informative error.
    """
    raise NotImplementedError(
        f"Configuration binding not yet implemented. "
        f"Cannot resolve {param_type} from config key '{config_key}'. "
        f"This feature will be added in a future update."
    )