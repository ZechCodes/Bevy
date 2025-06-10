"""
Async dependency resolution system for Bevy.

This module provides automatic detection and resolution of async dependency chains,
allowing for seamless integration of async factories with the existing sync API.
"""

import inspect
import types
from typing import Any, Awaitable, Type, TypeVar
from dataclasses import dataclass
from tramp.optionals import Optional
from bevy.hooks import Hook
from bevy.injection_types import CircularDependencyError, DependencyResolutionError
from bevy.factories import Factory

T = TypeVar('T')


@dataclass
class ChainInfo:
    """Information about a dependency resolution chain."""
    target_type: Type[Any]
    factories: dict[Type[Any], Any]  # Type -> Factory function
    has_async_factories: bool
    async_factories: set[Type[Any]]  # Types that have async factories
    resolution_order: list[Type[Any]]  # Order to resolve dependencies
    
    
class DependencyGraphTraversal:
    """Handles the traversal and analysis of dependency graphs."""
    
    def __init__(self, analyzer):
        self.analyzer = analyzer
        self.visited = set()
        self.factories = {}
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
        
    def analyze_dependency_chain(self, target_type: Type[T], **kwargs) -> ChainInfo:
        """
        Analyze the complete dependency chain for a target type.
        
        Returns ChainInfo with details about all dependencies and whether
        any require async resolution.
        
        **kwargs can include default_factory, qualifier, default - these affect
        the analysis of whether the final resolution will be async.
        """
        # For now, we'll cache based on just the target_type
        # TODO: Consider caching with resolution context if needed for performance
        cache_key = target_type
        if cache_key in self._chain_cache:
            cached_info = self._chain_cache[cache_key]
            # Analyze if resolution context affects async behavior
            return self._adjust_for_resolution_context(cached_info, **kwargs)
            
        # Use traversal class to build dependency graph
        traversal = DependencyGraphTraversal(self)
        has_async = traversal.traverse(target_type)
        
        # Check if we found any factories at all
        if not traversal.factories:
            # Check if we have resolution overrides that make this resolvable
            if not self._has_resolution_override(**kwargs):
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
            has_async_factories=has_async,
            async_factories=traversal.async_factories,
            resolution_order=traversal.resolution_order
        )
        
        # Cache result and adjust for resolution context
        self._chain_cache[target_type] = chain_info
        return self._adjust_for_resolution_context(chain_info, **kwargs)
    
    def _has_resolution_override(self, **kwargs) -> bool:
        """Check if kwargs provide ways to resolve without registered factories."""
        return (
            kwargs.get("default_factory") is not None or
            kwargs.get("default") is not None
        )
    
    def _adjust_for_resolution_context(self, chain_info: ChainInfo, **kwargs) -> ChainInfo:
        """
        Adjust chain info based on resolution context (default_factory, qualifier, etc.).
        
        This determines if resolution context overrides async behavior.
        For example, a sync default_factory should make resolution sync even if
        the registered factory would be async.
        """
        default_factory = kwargs.get("default_factory")
        if default_factory:
            # default_factory overrides registered factories
            # Check if the default_factory itself is async
            import inspect
            if inspect.iscoroutinefunction(default_factory):
                # Async default_factory makes resolution async
                return ChainInfo(
                    target_type=chain_info.target_type,
                    factories={chain_info.target_type: default_factory},
                    has_async_factories=True,
                    async_factories={chain_info.target_type},
                    resolution_order=[chain_info.target_type]
                )
            else:
                # Sync default_factory makes resolution sync
                return ChainInfo(
                    target_type=chain_info.target_type,
                    factories={chain_info.target_type: default_factory},
                    has_async_factories=False,
                    async_factories=set(),
                    resolution_order=[chain_info.target_type]
                )
        
        # Other resolution context (qualifier, default) doesn't change async behavior
        # of the underlying registered factories
        return chain_info
        
    def _get_factory_dependencies(self, factory) -> set[Type[Any]]:
        """Get the dependency types that a factory function requires.
        
        Uses the existing injection analysis system to properly detect dependencies
        based on @injectable configuration and Inject[T] annotations.
        """
        dependencies = set()
        
        try:
            from bevy.injections import analyze_function_signature, get_injection_info
            from bevy.injection_types import InjectionStrategy
            
            # First check if factory has @injectable metadata
            injection_info = get_injection_info(factory)
            if injection_info:
                # Use the factory's configured injection strategy
                injectable_params = injection_info['params']
            else:
                # No @injectable decorator - analyze with DEFAULT strategy
                # This matches the default behavior for non-decorated factories
                injectable_params = analyze_function_signature(factory, InjectionStrategy.DEFAULT)
            
            # Extract dependency types from injectable parameters
            for param_name, (param_type, options) in injectable_params.items():
                if param_name != 'container' and isinstance(param_type, type):
                    dependencies.add(param_type)
                        
        except (ValueError, TypeError) as e:
            # Signature inspection failures
            raise DependencyResolutionError(
                dependency_type=type(None),
                parameter_name="unknown",
                message=f"Failed to analyze factory signature for dependency analysis: {factory}. "
                       f"Error: {e}. Ensure factory is a valid callable."
            ) from e
        except Exception as e:
            # Injection analysis failures (annotation resolution, etc.)
            raise DependencyResolutionError(
                dependency_type=type(None),
                parameter_name="unknown",
                message=f"Failed to analyze injectable dependencies in factory {factory}. "
                       f"Error: {e}. Check that all type annotations are valid and "
                       f"injection configuration is correct."
            ) from e
            
        return dependencies
        
    def invalidate_cache(self, dependency_type: Type[Any] | None = None):
        """Invalidate dependency chain cache."""
        if dependency_type:
            self._chain_cache.pop(dependency_type, None)
        else:
            self._chain_cache.clear()


class DependenciesReady:
    """Resolver for synchronous dependency chains."""
    
    def __init__(self, container, target_type: Type[T], chain_info: ChainInfo, **kwargs):
        self.container = container
        self.target_type = target_type
        self.chain_info = chain_info
        self.resolution_kwargs = kwargs
        
    def get_result(self) -> T:
        """Synchronously resolve and return the dependency instance."""
        # Use container's sync resolution logic which handles all the edge cases
        # (default_factory, qualifier, default, caching, hooks, etc.)
        return self.container._get_sync(self.target_type, **self.resolution_kwargs)


class DependenciesPending:
    """Resolver for asynchronous dependency chains."""
    
    def __init__(self, container, target_type: Type[T], chain_info: ChainInfo, **kwargs):
        self.container = container
        self.target_type = target_type
        self.chain_info = chain_info
        self.resolution_kwargs = kwargs
        
    def get_result(self) -> Awaitable[T]:
        """Return coroutine that resolves the dependency instance."""
        return self._resolve_async_chain()
        
    async def _resolve_async_chain(self) -> T:
        """Asynchronously resolve the complete dependency chain."""
        # Import here to avoid circular import
        from bevy.containers import _in_async_resolution
        
        # Handle resolution context overrides first
        default_factory = self.resolution_kwargs.get("default_factory")
        if default_factory:
            # default_factory overrides everything - handle it directly
            if inspect.iscoroutinefunction(default_factory):
                # Async default factory - await it
                return await self._resolve_async_default_factory(default_factory)
            else:
                # Sync default factory - delegate to sync logic
                token = _in_async_resolution.set(True)
                try:
                    return self.container._get_sync(self.target_type, **self.resolution_kwargs)
                finally:
                    _in_async_resolution.reset(token)
        
        # Check for simple value defaults
        if "default" in self.resolution_kwargs:
            # Check if instance exists, otherwise return default
            existing = self.container._get_existing_instance(self.target_type)
            match existing:
                case Optional.Some(instance):
                    return instance
                case Optional.Nothing():
                    return self.resolution_kwargs["default"]
        
        # For qualified dependencies, use sync logic during async resolution
        if self.resolution_kwargs.get("qualifier"):
            token = _in_async_resolution.set(True)
            try:
                return self.container._get_sync(self.target_type, **self.resolution_kwargs)
            finally:
                _in_async_resolution.reset(token)
        
        # Standard async dependency chain resolution
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
                        if isinstance(factory, Factory):  # Factory object
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
                    if isinstance(factory, Factory):  # Factory object
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
    
    async def _resolve_async_default_factory(self, async_factory) -> T:
        """Resolve an async default_factory with proper caching and dependency injection."""
        # Check if we already have a cached result from this factory
        if async_factory in self.container.instances:
            return self.container.instances[async_factory]
        
        # Check parent container's factory cache
        if self.container._parent:
            if parent_result := self.container._parent._get_factory_cache_result(async_factory):
                # Cache in this container too for faster future access
                self.container.instances[async_factory] = parent_result
                return parent_result
        
        # Create new instance using async factory
        from inspect import signature
        factory_sig = signature(async_factory)
        if len(factory_sig.parameters) > 0:
            # Factory accepts parameters, use container for dependency injection
            instance = await self.container.call(async_factory, self.container)
        else:
            # Factory takes no parameters, call directly
            instance = await async_factory()
        
        # Cache the result using factory as key
        self.container.instances[async_factory] = instance
        return instance


# Removed unused AsyncContainerWrapper and AsyncDependencyMarker classes
# The simplified resolution approach doesn't need them.