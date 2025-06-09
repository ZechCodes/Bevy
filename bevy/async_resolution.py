"""
Async dependency resolution system for Bevy.

This module provides automatic detection and resolution of async dependency chains,
allowing for seamless integration of async factories with the existing sync API.
"""

import inspect
import types
from typing import Any, Awaitable, Type, TypeVar
from dataclasses import dataclass
from collections import defaultdict
from tramp.optionals import Optional
from bevy.hooks import Hook
from bevy.injection_types import CircularDependencyError, DependencyResolutionError

T = TypeVar('T')


@dataclass
class ChainInfo:
    """Information about a dependency resolution chain."""
    target_type: Type[Any]
    factories: dict[Type[Any], Any]  # Type -> Factory function
    dependencies: dict[Type[Any], set[Type[Any]]]  # Type -> Set of dependency types
    has_async_factories: bool
    async_factories: set[Type[Any]]  # Types that have async factories
    resolution_order: list[Type[Any]]  # Order to resolve dependencies
    
    
class DependencyGraphTraversal:
    """Handles the traversal and analysis of dependency graphs."""
    
    def __init__(self, analyzer):
        self.analyzer = analyzer
        self.visited = set()
        self.factories = {}
        self.dependencies = defaultdict(set)
        self.async_factories = set()
        self.resolution_order = []
        
    def traverse(self, target_type: Type[Any]) -> bool:
        """
        Traverse the dependency graph starting from target_type.
        Returns True if any dependencies in the chain are async.
        """
        return self._visit_dependency(target_type)
        
    def _visit_dependency(self, dep_type: Type[Any], visiting_stack: set[Type[Any]] | None = None) -> bool:
        """Visit a dependency type and return True if it's async."""
        if visiting_stack is None:
            visiting_stack = set()
        else:
            visiting_stack = visiting_stack.copy()
            
        # Check for circular dependencies
        if dep_type in visiting_stack:
            cycle_chain = list(visiting_stack) + [dep_type]
            raise CircularDependencyError(cycle_chain)
        
        if dep_type in self.visited:
            return dep_type in self.async_factories
            
        self.visited.add(dep_type)
        visiting_stack.add(dep_type)
        
        # Find factory for this type
        match self.analyzer.registry.find_factory_for_type(dep_type):
            case Optional.Some(factory):
                pass
            case Optional.Nothing():
                factory = None
        if factory is None:
            # No factory found - this will be handled by existing error handling
            return False
            
        self.factories[dep_type] = factory
        
        # Check if factory is async
        is_async = inspect.iscoroutinefunction(factory)
        if is_async:
            self.async_factories.add(dep_type)
            
        # Analyze factory dependencies
        factory_deps = self.analyzer._get_factory_dependencies(factory)
        self.dependencies[dep_type] = factory_deps
        
        # Recursively check dependencies
        dep_has_async = False
        for dep in factory_deps:
            if self._visit_dependency(dep, visiting_stack):
                dep_has_async = True
                
        # If any dependency is async, this chain is async
        if dep_has_async:
            self.async_factories.add(dep_type)
            is_async = True
            
        self.resolution_order.append(dep_type)
        return is_async


class DependencyAnalyzer:
    """Analyzes dependency chains to determine if async resolution is needed."""
    
    def __init__(self, registry, parent_container=None):
        self.registry = registry
        self.parent_container = parent_container
        self._chain_cache: dict[Type[Any], ChainInfo] = {}
        
    def analyze_dependency_chain(self, target_type: Type[T]) -> ChainInfo:
        """
        Analyze the complete dependency chain for a target type.
        
        Returns ChainInfo with details about all dependencies and whether
        any require async resolution.
        """
        if target_type in self._chain_cache:
            return self._chain_cache[target_type]
            
        # Use traversal class to build dependency graph
        traversal = DependencyGraphTraversal(self)
        has_async = traversal.traverse(target_type)
        
        # Check if we found any factories at all
        if not traversal.factories:
            # Handle types that don't have __name__ attribute (like UnionType)
            type_name = getattr(target_type, '__name__', str(target_type))
            raise DependencyResolutionError(
                dependency_type=target_type,
                parameter_name="unknown",
                message=f"No factory found for dependency: {type_name}"
            )
        
        # Build chain info
        chain_info = ChainInfo(
            target_type=target_type,
            factories=traversal.factories,
            dependencies=dict(traversal.dependencies),
            has_async_factories=has_async,
            async_factories=traversal.async_factories,
            resolution_order=traversal.resolution_order
        )
        
        # Cache result
        self._chain_cache[target_type] = chain_info
        return chain_info
        
    def _get_factory_dependencies(self, factory) -> set[Type[Any]]:
        """Get the dependency types that a factory function requires.
        
        Only analyzes explicit parameter type annotations. No bytecode analysis.
        
        If a factory needs dependencies, they must be declared as typed parameters.
        This is explicit, safe, and doesn't rely on fragile bytecode analysis.
        """
        dependencies = set()
        
        try:
            sig = inspect.signature(factory)
            
            # Only analyze explicit parameter types
            for param_name, param in sig.parameters.items():
                if param_name == 'container':
                    continue
                    
                if param.annotation and param.annotation != inspect.Parameter.empty:
                    if isinstance(param.annotation, type):
                        dependencies.add(param.annotation)
                        
        except Exception:
            # If analysis fails, return empty set - safer than guessing
            pass
            
        return dependencies
        
    def invalidate_cache(self, dependency_type: Type[Any] | None = None):
        """Invalidate dependency chain cache."""
        if dependency_type:
            self._chain_cache.pop(dependency_type, None)
        else:
            self._chain_cache.clear()


class DependenciesReady:
    """Resolver for synchronous dependency chains."""
    
    def __init__(self, container, target_type: Type[T], chain_info: ChainInfo):
        self.container = container
        self.target_type = target_type
        self.chain_info = chain_info
        
    def get_result(self) -> T:
        """Synchronously resolve and return the dependency instance."""
        # Check if already cached locally first
        if self.target_type in self.container.instances:
            return self.container.instances[self.target_type]
            
        # Check parent containers
        if self.container._parent:
            parent_instance = self.container._parent._get_existing_instance(self.target_type)
            match parent_instance:
                case Optional.Some(instance):
                    # Cache in current container and return
                    self.container.instances[self.target_type] = instance
                    return instance
                case Optional.Nothing():
                    pass
                    
        # Create new instance and cache it (same as container.get() logic)
        instance = self.container._create_instance(self.target_type)
        # Apply hooks and cache the instance
        instance = self.container.registry.hooks[Hook.GOT_INSTANCE].filter(self.container, instance)
        self.container.instances[self.target_type] = instance
        return instance


class DependenciesPending:
    """Resolver for asynchronous dependency chains."""
    
    def __init__(self, container, target_type: Type[T], chain_info: ChainInfo):
        self.container = container
        self.target_type = target_type
        self.chain_info = chain_info
        
    def get_result(self) -> Awaitable[T]:
        """Return coroutine that resolves the dependency instance."""
        return self._resolve_async_chain()
        
    async def _resolve_async_chain(self) -> T:
        """Asynchronously resolve the complete dependency chain."""
        # Import here to avoid circular import
        from bevy.containers import _in_async_resolution
        
        # Check if the target instance already exists (including parent containers)
        existing_instance = self.container._get_existing_instance(self.target_type)
        match existing_instance:
            case Optional.Some(instance):
                return instance
            case Optional.Nothing():
                pass
                
        # Check parent container for existing instance
        if self.container._parent:
            parent_instance = self.container._parent._get_existing_instance(self.target_type)
            match parent_instance:
                case Optional.Some(instance):
                    # Cache in current container and return
                    self.container.instances[self.target_type] = instance
                    return instance
                case Optional.Nothing():
                    pass
        
        # Strategy: Resolve all async dependencies first in dependency order,
        # then resolve sync dependencies. This ensures sync factories get
        # actual instances, not coroutines.
        
        # Set context flag to prevent async detection during resolution
        token = _in_async_resolution.set(True)
        try:
            # Phase 1: Resolve all async dependencies
            for dep_type in self.chain_info.resolution_order:
                # Check if already exists (including parent containers)
                existing = self.container._get_existing_instance(dep_type)
                match existing:
                    case Optional.Some(_):
                        continue  # Already resolved
                    case Optional.Nothing():
                        pass
                    
                if dep_type in self.chain_info.async_factories:
                    factory = self.chain_info.factories[dep_type]
                    if inspect.iscoroutinefunction(factory):
                        # Async factory
                        if hasattr(factory, 'factory'):  # Factory object
                            instance = await factory(self.container)
                        else:  # Function factory - use dependency injection
                            instance = await self.container.call(factory, self.container)
                        self.container.instances[dep_type] = instance
            
            # Phase 2: Resolve remaining dependencies (sync factories, even if they depend on async)
            for dep_type in self.chain_info.resolution_order:
                # Check if already exists (including parent containers)
                existing = self.container._get_existing_instance(dep_type)
                match existing:
                    case Optional.Some(_):
                        continue  # Already resolved
                    case Optional.Nothing():
                        pass
                    
                # Check if this is a sync factory (even if it's marked as async due to dependencies)
                factory = self.chain_info.factories[dep_type]
                if not inspect.iscoroutinefunction(factory):
                    # Sync factory
                    if hasattr(factory, 'factory'):  # Factory object
                        instance = factory(self.container)
                    else:  # Function factory - use dependency injection
                        instance = self.container.call(factory, self.container)
                    self.container.instances[dep_type] = instance
        finally:
            # Reset context flag
            _in_async_resolution.reset(token)
        
        # Return the target instance (should now be resolved)
        final_instance = self.container._get_existing_instance(self.target_type)
        match final_instance:
            case Optional.Some(instance):
                return instance
            case Optional.Nothing():
                raise ValueError(f"Failed to resolve {self.target_type}")


# Removed unused AsyncContainerWrapper and AsyncDependencyMarker classes
# The simplified resolution approach doesn't need them.