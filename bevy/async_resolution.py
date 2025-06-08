"""
Async dependency resolution system for Bevy.

This module provides automatic detection and resolution of async dependency chains,
allowing for seamless integration of async factories with the existing sync API.
"""

import inspect
from typing import Any, Awaitable, Type, Dict, Set, List, Union, TypeVar
from dataclasses import dataclass
from collections import defaultdict
from tramp.optionals import Optional
from bevy.hooks import Hook

T = TypeVar('T')


@dataclass
class ChainInfo:
    """Information about a dependency resolution chain."""
    target_type: Type[Any]
    factories: Dict[Type[Any], Any]  # Type -> Factory function
    dependencies: Dict[Type[Any], Set[Type[Any]]]  # Type -> Set of dependency types
    has_async_factories: bool
    async_factories: Set[Type[Any]]  # Types that have async factories
    resolution_order: List[Type[Any]]  # Order to resolve dependencies
    
    
class DependencyAnalyzer:
    """Analyzes dependency chains to determine if async resolution is needed."""
    
    def __init__(self, registry, parent_container=None):
        self.registry = registry
        self.parent_container = parent_container
        self._chain_cache: Dict[Type[Any], ChainInfo] = {}
        
    def analyze_dependency_chain(self, target_type: Type[T]) -> ChainInfo:
        """
        Analyze the complete dependency chain for a target type.
        
        Returns ChainInfo with details about all dependencies and whether
        any require async resolution.
        """
        if target_type in self._chain_cache:
            return self._chain_cache[target_type]
            
        # Build dependency graph
        visited = set()
        factories = {}
        dependencies = defaultdict(set)
        async_factories = set()
        resolution_order = []
        
        def visit_dependency(dep_type: Type[Any], visiting_stack: Set[Type[Any]] = None) -> bool:
            """Visit a dependency type and return True if it's async."""
            if visiting_stack is None:
                visiting_stack = set()
                
            # Check for circular dependencies
            if dep_type in visiting_stack:
                cycle_chain = list(visiting_stack) + [dep_type]
                from bevy.injection_types import CircularDependencyError
                raise CircularDependencyError(cycle_chain)
            
            if dep_type in visited:
                return dep_type in async_factories
                
            visited.add(dep_type)
            visiting_stack.add(dep_type)
            
            # Find factory for this type
            factory = self._find_factory_for_type(dep_type)
            if factory is None:
                # No factory found - this will be handled by existing error handling
                return False
                
            factories[dep_type] = factory
            
            # Check if factory is async
            is_async = inspect.iscoroutinefunction(factory)
            if is_async:
                async_factories.add(dep_type)
                
            # Analyze factory dependencies
            factory_deps = self._get_factory_dependencies(factory)
            dependencies[dep_type] = factory_deps
            
            # Recursively check dependencies
            dep_has_async = False
            for dep in factory_deps:
                if visit_dependency(dep, visiting_stack.copy()):
                    dep_has_async = True
                    
            # If any dependency is async, this chain is async
            if dep_has_async:
                async_factories.add(dep_type)
                is_async = True
                
            resolution_order.append(dep_type)
            visiting_stack.discard(dep_type)  # Remove from visiting stack when done
            return is_async
            
        # Start analysis from target type
        has_async = visit_dependency(target_type)
        
        # Check if we found any factories at all
        if not factories:
            from bevy.injection_types import DependencyResolutionError
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
            factories=factories,
            dependencies=dict(dependencies),
            has_async_factories=has_async,
            async_factories=async_factories,
            resolution_order=resolution_order
        )
        
        # Cache result
        self._chain_cache[target_type] = chain_info
        return chain_info
        
    def _find_factory_for_type(self, dependency_type: Type[Any]) -> Any:
        """Find factory for a given type - mirrors Container._find_factory_for_type logic."""
        if not isinstance(dependency_type, type):
            return None
            
        # Check current registry first
        for factory_type, factory in self.registry.factories.items():
            try:
                if issubclass(dependency_type, factory_type):
                    return factory
            except TypeError:
                # Handle cases where issubclass fails
                continue
        
        # Check parent container registries if not found
        if self.parent_container:
            return self.parent_container._dependency_analyzer._find_factory_for_type(dependency_type)
                
        return None
        
    def _get_factory_dependencies(self, factory) -> Set[Type[Any]]:
        """Get the dependency types that a factory function requires."""
        dependencies = set()
        
        # For factory functions that take a container parameter, we need to analyze
        # what types they might call container.get() on. For now, we'll use a 
        # simplified approach but this could be enhanced with AST analysis.
        
        try:
            sig = inspect.signature(factory)
            
            # Check if this is a standard factory function with container parameter
            if len(sig.parameters) == 1 and 'container' in sig.parameters:
                # This is a standard Bevy factory function
                # We need to analyze what it calls container.get() on
                # For now, we'll use a heuristic approach
                
                # Look at the function's code to find container.get() calls
                import dis
                import types
                
                # Get the factory's bytecode
                if hasattr(factory, '__code__'):
                    code = factory.__code__
                    
                    # Look for LOAD_ATTR instructions that might be .get() calls
                    instructions = list(dis.get_instructions(code))
                    for i, instr in enumerate(instructions):
                        if (instr.opname == 'LOAD_ATTR' and 
                            instr.argval == 'get' and 
                            i > 0 and 
                            instructions[i-1].opname == 'LOAD_FAST' and
                            instructions[i-1].argval == 'container'):
                            
                            # This looks like container.get() - try to find what type is being requested
                            # Look ahead for the type being loaded
                            for j in range(i+1, min(i+5, len(instructions))):
                                if instructions[j].opname in ['LOAD_GLOBAL', 'LOAD_FAST']:
                                    # Try to resolve the type from the factory's globals
                                    type_name = instructions[j].argval
                                    if hasattr(factory, '__globals__') and type_name in factory.__globals__:
                                        dep_type = factory.__globals__[type_name]
                                        if isinstance(dep_type, type):
                                            dependencies.add(dep_type)
                                    break
                
            else:
                # Non-standard factory - analyze parameters
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
        
    def invalidate_cache(self, dependency_type: Type[Any] = None):
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
        # Import the context variable at the top of the async function
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
                        # Async factory - resolve it and cache normally
                        instance = await factory(self.container)
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
                    # Sync factory - call normally (async deps should already be resolved)
                    instance = factory(self.container)
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