"""
Core types and enums for the Bevy dependency injection system.

This module defines the type aliases, enums, and metadata classes used
for type-safe dependency injection configuration with full IDE support.

Example:
    Basic dependency injection:
    
    >>> from bevy import injectable, Inject
    >>> 
    >>> @injectable
    >>> def process_data(service: Inject[UserService]):
    ...     return service.process()
    
    With options:
    
    >>> @injectable
    >>> def advanced_processing(
    ...     primary_db: Inject[Database, Options(qualifier="primary")],
    ...     logger: Inject[Logger, Options(default_factory=lambda: Logger("app"))]
    ... ):
    ...     pass
"""
from enum import Enum
from types import UnionType
from typing import Annotated, Callable, get_args, get_origin, Optional, Union


class DependencyResolutionError(Exception):
    """
    Raised when a dependency cannot be resolved during injection.
    
    This is the only exception that should be caught by the injection system
    for fallback handling (optional dependencies, non-strict mode, etc.).
    All other exceptions should bubble up normally.
    """
    def __init__(self, dependency_type: type, parameter_name: str, message: str = None):
        self.dependency_type = dependency_type
        self.parameter_name = parameter_name
        if message is None:
            message = f"Cannot resolve dependency {dependency_type.__name__} for parameter '{parameter_name}'"
        super().__init__(message)


# Type alias for dependency injection using Python 3.12+ syntax
type Inject[T, Opts: object] = Annotated[T, Opts]


class InjectionStrategy(Enum):
    """
    Strategy for determining which parameters to inject.
    
    Example:
        >>> @injectable(strategy=InjectionStrategy.REQUESTED_ONLY)
        >>> def explicit_injection(service: Inject[UserService], manual: str):
        ...     pass  # Only 'service' will be injected
        
        >>> @injectable(strategy=InjectionStrategy.ANY_NOT_PASSED)
        >>> def auto_injection(service: UserService, manual: str):
        ...     pass  # Both 'service' and 'manual' can be injected if not provided
        
        >>> @injectable(strategy=InjectionStrategy.ONLY, params=["service"])
        >>> def selective_injection(service: UserService, other: Database):
        ...     pass  # Only 'service' will be injected, 'other' must be provided
    """
    DEFAULT = "default"                  # Maps to REQUESTED_ONLY
    REQUESTED_ONLY = "requested_only"    # Only inject Inject[T] parameters
    ANY_NOT_PASSED = "any_not_passed"    # Inject any typed param not passed
    ONLY = "only"                        # Inject only specified parameters


class TypeMatchingStrategy(Enum):
    """
    Strategy for matching types during dependency resolution.
    
    Example:
        >>> @injectable(type_matching=TypeMatchingStrategy.EXACT_TYPE)
        >>> def strict_matching(service: Inject[UserService]):
        ...     pass  # Only exact UserService type accepted
        
        >>> @injectable(type_matching=TypeMatchingStrategy.SUBCLASS) 
        >>> def flexible_matching(service: Inject[UserService]):
        ...     pass  # UserService or any subclass accepted
    """
    DEFAULT = "default"                  # Maps to SUBCLASS
    SUBCLASS = "subclass"                # Allow subclasses (current behavior)
    STRUCTURAL = "structural"            # Allow protocols/duck typing
    EXACT_TYPE = "exact_type"            # Exact type match only


class Options:
    """
    Metadata options for dependency injection.
    
    Used with Inject[T, Options(...)] to configure dependency behavior.
    
    Example:
        >>> # Qualified dependencies
        >>> @injectable
        >>> def func(
        ...     primary_db: Inject[Database, Options(qualifier="primary")],
        ...     backup_db: Inject[Database, Options(qualifier="backup")]
        ... ):
        ...     pass
        
        >>> # Default factory
        >>> @injectable
        >>> def func(
        ...     logger: Inject[Logger, Options(default_factory=lambda: Logger("app"))]
        ... ):
        ...     pass
        
    """
    
    def __init__(
        self,
        qualifier: Optional[str] = None,
        default_factory: Optional[Callable] = None,
        cache_factory_result: bool = True
    ):
        """
        Initialize injection options.
        
        Args:
            qualifier: String qualifier to distinguish multiple implementations
            default_factory: Factory function to create default value if dependency not found
            cache_factory_result: Whether to cache the result of default_factory calls.
                                True (default): Same factory = same instance (performance)
                                False: Fresh instance on each call (testing scenarios)
        """
        self.qualifier = qualifier
        self.default_factory = default_factory
        self.cache_factory_result = cache_factory_result
    
    def __repr__(self) -> str:
        """Readable representation of options."""
        parts = []
        if self.qualifier:
            parts.append(f"qualifier='{self.qualifier}'")
        if self.default_factory:
            parts.append(f"default_factory={self.default_factory.__name__}")
        if not self.cache_factory_result:
            parts.append("cache_factory_result=False")
        
        return f"Options({', '.join(parts)})"


def extract_injection_info(annotation):
    """
    Extract injection metadata from type annotation.
    
    Args:
        annotation: Type annotation to analyze
        
    Returns:
        Tuple of (actual_type, options) where options is None for non-injectable types
    """
    if get_origin(annotation) is Inject:
        args = get_args(annotation)
        actual_type = args[0]
        options = args[1] if len(args) > 1 else None
        return actual_type, options

    return annotation, None


def is_optional_type(type_annotation) -> bool:
    """
    Check if a type annotation represents an optional type (Union with None).
    
    Args:
        type_annotation: Type annotation to check
        
    Returns:
        True if the type includes None (is optional)
    """
    origin = get_origin(type_annotation)
    if origin is not None:
        args = get_args(type_annotation)
        # Check for Union types that include None
        if origin in {Union, UnionType}:
            return type(None) in args

    return False


def get_non_none_type(type_annotation):
    """
    Extract the non-None type from an optional type annotation.
    
    Args:
        type_annotation: Optional type annotation (e.g., UserService | None)
        
    Returns:
        The non-None type from the union, or the original type if not optional
    """
    origin = get_origin(type_annotation)
    if origin is not None:
        args = get_args(type_annotation)
        # Check for Union types that include None
        if origin in {Union, UnionType}:
            non_none_types = [arg for arg in args if arg is not type(None)]
            return non_none_types[0] if non_none_types else type_annotation

    return type_annotation