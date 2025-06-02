"""
Core types and enums for the Bevy dependency injection system.

This module defines the type aliases, enums, and metadata classes used
for type-safe dependency injection configuration.
"""

from typing import Annotated, Optional, Callable, get_origin, get_args
from enum import Enum


# Type alias for dependency injection using Python 3.12+ syntax
type Inject[T, Opts: object] = Annotated[T, Opts]


class InjectionStrategy(Enum):
    """Strategy for determining which parameters to inject."""
    DEFAULT = "default"                  # Maps to REQUESTED_ONLY
    REQUESTED_ONLY = "requested_only"    # Only inject Inject[T] parameters
    ANY_NOT_PASSED = "any_not_passed"    # Inject any typed param not passed
    ONLY = "only"                        # Inject only specified parameters


class TypeMatchingStrategy(Enum):
    """Strategy for matching types during dependency resolution."""
    DEFAULT = "default"                  # Maps to SUBCLASS
    SUBCLASS = "subclass"                # Allow subclasses (current behavior)
    STRUCTURAL = "structural"            # Allow protocols/duck typing
    EXACT_TYPE = "exact_type"            # Exact type match only


class Options:
    """Metadata options for dependency injection."""
    
    def __init__(
        self,
        qualifier: Optional[str] = None,
        from_config: Optional[str] = None,
        default_factory: Optional[Callable] = None
    ):
        """
        Initialize injection options.
        
        Args:
            qualifier: String qualifier to distinguish multiple implementations
            from_config: Configuration key to bind value from
            default_factory: Factory function to create default value if dependency not found
        """
        self.qualifier = qualifier
        self.from_config = from_config
        self.default_factory = default_factory
    
    def __repr__(self) -> str:
        """Readable representation of options."""
        parts = []
        if self.qualifier:
            parts.append(f"qualifier='{self.qualifier}'")
        if self.from_config:
            parts.append(f"from_config='{self.from_config}'")
        if self.default_factory:
            parts.append(f"default_factory={self.default_factory.__name__}")
        
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
        if hasattr(origin, '__name__') and origin.__name__ == 'UnionType':
            return type(None) in args
        # Handle typing.Union
        if str(origin).startswith('typing.Union'):
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
        # Handle Union types with None
        if hasattr(origin, '__name__') and origin.__name__ == 'UnionType':
            non_none_types = [arg for arg in args if arg is not type(None)]
            return non_none_types[0] if non_none_types else type_annotation
        # Handle typing.Union
        if str(origin).startswith('typing.Union'):
            non_none_types = [arg for arg in args if arg is not type(None)]
            return non_none_types[0] if non_none_types else type_annotation
    return type_annotation