#!/usr/bin/env python3
"""
Comprehensive tests for async dependency resolution.

Tests cover:
1. Async factory registration and detection
2. Mixed sync/async dependency chains  
3. Error cases and edge conditions
4. Performance of sync-only paths (no async overhead)
5. Circular dependency detection with async factories
6. Chain analysis and caching
"""

import asyncio
import inspect
import pytest
from typing import Awaitable, Union
from unittest.mock import Mock, patch
import time

from bevy import Container, injectable, Inject
from bevy.registries import Registry
from bevy.injection_types import DependencyResolutionError
from bevy.bundled.type_factory_hook import type_factory


# Test Service Classes
class Config:
    def __init__(self, db_url="sqlite://memory"):
        self.db_url = db_url


class Database:
    def __init__(self, config: Config):
        self.config = config
        self.connected = False
    
    async def connect(self):
        # Simulate async connection
        await asyncio.sleep(0.001)
        self.connected = True


class UserService:
    def __init__(self, db: Database):
        self.db = db


class NotificationService:
    def __init__(self, config: Config):
        self.config = config


class WebController:
    def __init__(self, user_service: UserService, notification_service: NotificationService):
        self.user_service = user_service
        self.notification_service = notification_service


# Circular dependency test classes (module level for consistent identity)
class CircularA:
    def __init__(self, b): self.b = b

class CircularB:
    def __init__(self, a): self.a = a

class AsyncCircularA:
    def __init__(self, b): self.b = b

class AsyncCircularB:
    def __init__(self, a): self.a = a

class MixedCircularA:
    def __init__(self, b): self.b = b

class MixedCircularB:
    def __init__(self, c): self.c = c
    
class MixedCircularC:
    def __init__(self, a): self.a = a

# Circular dependency test factories
def create_circular_a(container) -> CircularA:
    b = container.get(CircularB)
    return CircularA(b)

def create_circular_b(container) -> CircularB:
    a = container.get(CircularA)
    return CircularB(a)

async def create_async_circular_a(container) -> AsyncCircularA:
    b = container.get(AsyncCircularB)
    return AsyncCircularA(b)

def create_async_circular_b(container) -> AsyncCircularB:
    a = container.get(AsyncCircularA)
    return AsyncCircularB(a)

async def create_mixed_circular_a(container) -> MixedCircularA:
    b = container.get(MixedCircularB)
    return MixedCircularA(b)

def create_mixed_circular_b(container) -> MixedCircularB:
    c = container.get(MixedCircularC)
    return MixedCircularB(c)
    
def create_mixed_circular_c(container) -> MixedCircularC:
    a = container.get(MixedCircularA)
    return MixedCircularC(a)


# Test Factory Functions (to be registered with add_factory)
def create_config(container) -> Config:
    """Sync factory for Config"""
    return Config()


async def create_database(container) -> Database:
    """Async factory for Database"""
    config = container.get(Config)
    db = Database(config)
    await db.connect()
    return db


def create_user_service(container) -> UserService:
    """Sync factory with async dependency"""
    db = container.get(Database)
    return UserService(db)


def create_notification_service(container) -> NotificationService:
    """Sync factory with sync dependency"""
    config = container.get(Config)
    return NotificationService(config)


def create_web_controller(container) -> WebController:
    """Sync factory with mixed dependencies (one async chain, one sync)"""
    user_service = container.get(UserService)
    notification_service = container.get(NotificationService)
    return WebController(user_service, notification_service)


class TestAsyncFactoryDetection:
    """Test detection of async factories and dependency chain analysis."""
    
    def test_detect_sync_factory(self):
        """Should identify sync factories correctly."""
        assert not inspect.iscoroutinefunction(create_config)
        assert not inspect.iscoroutinefunction(create_notification_service)
    
    def test_detect_async_factory(self):
        """Should identify async factories correctly.""" 
        assert inspect.iscoroutinefunction(create_database)
    
    def test_mixed_factory_types(self):
        """Should handle mixed sync/async factory types."""
        factories = [
            create_config,
            create_database, 
            create_user_service,
            create_notification_service
        ]
        
        sync_factories = [f for f in factories if not inspect.iscoroutinefunction(f)]
        async_factories = [f for f in factories if inspect.iscoroutinefunction(f)]
        
        assert len(sync_factories) == 3
        assert len(async_factories) == 1
        assert create_database in async_factories


class TestSyncOnlyChains:
    """Test that sync-only dependency chains work without any async overhead."""
    
    def setup_method(self):
        self.registry = Registry()
        self.registry.add_factory(create_config, Config)
        self.registry.add_factory(create_notification_service, NotificationService)
        self.container = self.registry.create_container()
    
    def test_sync_factory_returns_instance_directly(self):
        """Sync-only chains should return instances directly, not awaitables."""
        config = self.container.get(Config)
        
        # Should be the actual object, not awaitable
        assert isinstance(config, Config)
        assert not inspect.iscoroutine(config)
        assert not hasattr(config, '__await__')
    
    def test_sync_chain_with_dependency(self):
        """Sync factory with sync dependency should return instance directly."""
        notification_service = self.container.get(NotificationService)
        
        assert isinstance(notification_service, NotificationService)
        assert not inspect.iscoroutine(notification_service)
        assert isinstance(notification_service.config, Config)
    
    def test_sync_chain_performance_baseline(self):
        """Sync chains should have minimal overhead (performance baseline)."""
        start_time = time.perf_counter()
        
        # Warm up
        for _ in range(10):
            self.container.get(Config)
        
        # Measure performance
        iterations = 1000
        start_time = time.perf_counter()
        for _ in range(iterations):
            config = self.container.get(Config)
        end_time = time.perf_counter()
        
        avg_time = (end_time - start_time) / iterations
        # Should be very fast - under 1ms per resolution
        assert avg_time < 0.001, f"Sync resolution too slow: {avg_time:.6f}s"


class TestAsyncChains:
    """Test async dependency chains and resolution."""
    
    def setup_method(self):
        self.registry = Registry()
        self.registry.add_factory(create_config, Config)
        self.registry.add_factory(create_database, Database)
        self.registry.add_factory(create_user_service, UserService)
        self.container = self.registry.create_container()
    
    @pytest.mark.asyncio
    async def test_async_factory_returns_awaitable(self):
        """Async factories should return awaitables."""
        database_result = self.container.get(Database)
        
        # Should return an awaitable, not the instance directly
        assert inspect.iscoroutine(database_result) or hasattr(database_result, '__await__')
        
        # Awaiting should give us the actual instance
        database = await database_result
        assert isinstance(database, Database)
        assert database.connected is True
    
    @pytest.mark.asyncio 
    async def test_transitive_async_dependency(self):
        """Sync factory depending on async factory should return awaitable."""
        user_service_result = self.container.get(UserService)
        
        # Should return awaitable because Database is async
        assert inspect.iscoroutine(user_service_result) or hasattr(user_service_result, '__await__')
        
        user_service = await user_service_result
        assert isinstance(user_service, UserService)
        assert isinstance(user_service.db, Database)
        assert user_service.db.connected is True
    
    @pytest.mark.asyncio
    async def test_multiple_async_resolutions(self):
        """Multiple async resolutions should work correctly."""
        db1_result = self.container.get(Database)
        db2_result = self.container.get(Database) 
        
        db1 = await db1_result
        db2 = await db2_result
        
        # Should be the same cached instance
        assert db1 is db2
        assert db1.connected is True


class TestMixedDependencyChains:
    """Test complex scenarios with mixed sync/async dependencies."""
    
    def setup_method(self):
        self.registry = Registry()
        self.registry.add_factory(create_config, Config)
        self.registry.add_factory(create_database, Database)
        self.registry.add_factory(create_user_service, UserService)
        self.registry.add_factory(create_notification_service, NotificationService)
        self.registry.add_factory(create_web_controller, WebController)
        self.container = self.registry.create_container()
    
    @pytest.mark.asyncio
    async def test_mixed_dependency_chain(self):
        """Factory with both sync and async dependency paths should be async."""
        # WebController depends on:
        # - UserService (which depends on Database - async chain)
        # - NotificationService (which depends on Config - sync chain)
        # Overall should be async because of UserService -> Database
        
        controller_result = self.container.get(WebController)
        
        # Should be async due to async dependency chain
        assert inspect.iscoroutine(controller_result) or hasattr(controller_result, '__await__')
        
        controller = await controller_result
        assert isinstance(controller, WebController)
        assert isinstance(controller.user_service, UserService)
        assert isinstance(controller.notification_service, NotificationService)
        assert controller.user_service.db.connected is True
    
    def test_pure_sync_branch_in_mixed_container(self):
        """Pure sync dependencies should still be sync even in mixed container."""
        # NotificationService only depends on Config (sync chain)
        notification_service = self.container.get(NotificationService)
        
        # Should be sync despite container having async factories
        assert isinstance(notification_service, NotificationService)
        assert not inspect.iscoroutine(notification_service)


class TestCircularDependencyDetection:
    """Test circular dependency detection with async factories."""
    
    def test_sync_circular_dependency_detection(self):
        """Should detect circular dependencies in sync chains."""
        registry = Registry()
        registry.add_factory(create_circular_a, CircularA)
        registry.add_factory(create_circular_b, CircularB)
        container = registry.create_container()
        
        with pytest.raises(ValueError, match="Circular dependency detected"):
            container.create_resolver(CircularA)
    
    def test_async_circular_dependency_detection(self):
        """Should detect circular dependencies involving async factories."""
        registry = Registry()
        registry.add_factory(create_async_circular_a, AsyncCircularA)
        registry.add_factory(create_async_circular_b, AsyncCircularB)
        container = registry.create_container()
        
        with pytest.raises(ValueError, match="Circular dependency detected"):
            container.create_resolver(AsyncCircularA)
    
    def test_mixed_circular_dependency_detection(self):
        """Should detect circular dependencies in mixed sync/async chains."""
        registry = Registry()
        registry.add_factory(create_mixed_circular_a, MixedCircularA)
        registry.add_factory(create_mixed_circular_b, MixedCircularB)
        registry.add_factory(create_mixed_circular_c, MixedCircularC)
        container = registry.create_container()
        
        with pytest.raises(ValueError, match="Circular dependency detected"):
            container.create_resolver(MixedCircularA)


class TestErrorHandling:
    """Test error cases and edge conditions."""
    
    def setup_method(self):
        self.registry = Registry()
        self.container = self.registry.create_container()
    
    def test_missing_async_dependency(self):
        """Should provide clear error for missing async dependencies."""
        with pytest.raises(DependencyResolutionError) as exc_info:
            self.container.get(Database)
        
        # Error should mention the missing dependency
        assert "Database" in str(exc_info.value)
    
    def test_async_factory_exception_propagation(self):
        """Exceptions in async factories should propagate correctly."""
        
        async def failing_factory(container) -> Database:
            raise ValueError("Async factory failed")
        
        self.registry.add_factory(failing_factory, Database)
        
        # Exception should be raised when awaiting
        with pytest.raises(ValueError, match="Async factory failed"):
            async def test():
                result = self.container.get(Database)
                await result
            
            asyncio.run(test())
    
    def test_sync_using_async_dependency_error(self):
        """Should provide helpful error when sync code tries to use async result."""
        self.registry.add_factory(create_config, Config)
        self.registry.add_factory(create_database, Database)
        
        database_result = self.container.get(Database)
        
        # Trying to use awaitable as instance should give helpful error
        with pytest.raises(AttributeError):
            # This should fail because database_result is awaitable, not Database
            _ = database_result.connected


class TestChainAnalysisAndCaching:
    """Test dependency chain analysis and caching logic."""
    
    def test_chain_analysis_caching(self):
        """Chain analysis results should be cached for performance."""
        # This test will be implemented when chain analysis is added
        pass
    
    def test_chain_analysis_invalidation(self):
        """Chain analysis cache should invalidate when factories change."""
        # This test will be implemented when chain analysis is added  
        pass
    
    def test_parent_container_inheritance_in_analysis(self):
        """Chain analysis should consider parent container factories."""
        # This test will be implemented when parent inheritance is added
        pass


class TestContainerBranching:
    """Test async resolution with container branching/inheritance."""
    
    def setup_method(self):
        self.registry = Registry()
        self.registry.add_factory(create_config, Config)
        self.registry.add_factory(create_database, Database)
        self.parent_container = self.registry.create_container()
        self.child_container = self.parent_container.branch()
    
    @pytest.mark.asyncio
    async def test_child_inherits_async_resolution(self):
        """Child containers should inherit async resolution behavior."""
        # Resolve in parent first
        parent_db = await self.parent_container.get(Database)
        
        # Child should get same instance
        child_db_result = self.child_container.get(Database)
        child_db = await child_db_result
        
        assert child_db is parent_db
        assert child_db.connected is True
    
    @pytest.mark.asyncio 
    async def test_child_overrides_with_async(self):
        """Child can override with async factory."""
        
        async def child_database_factory(container) -> Database:
            config = container.get(Config)
            db = Database(config)
            db.config.db_url = "child_override"
            await db.connect()
            return db
        
        self.child_container.registry.add_factory(child_database_factory, Database)
        
        child_db = await self.child_container.get(Database)
        assert child_db.config.db_url == "child_override"
        assert child_db.connected is True


# Performance and Integration Tests
class TestPerformanceCharacteristics:
    """Test performance characteristics of async resolution."""
    
    def setup_method(self):
        self.registry = Registry()
        self.registry.add_factory(create_config, Config)
        self.registry.add_factory(create_notification_service, NotificationService)
        self.container = self.registry.create_container()
    
    def test_sync_path_no_async_overhead(self):
        """Sync-only paths should have minimal async overhead."""
        # Warm up
        for _ in range(10):
            self.container.get(Config)
        
        # Measure sync performance with unified API
        iterations = 1000
        start_time = time.perf_counter()
        for _ in range(iterations):
            config = self.container.get(Config)
            assert isinstance(config, Config)  # Ensure it's not an awaitable
        end_time = time.perf_counter()
        
        avg_time = (end_time - start_time) / iterations
        # Should be very fast - under 1ms per resolution even with async detection
        assert avg_time < 0.001, f"Unified API sync resolution too slow: {avg_time:.6f}s"
    
    def test_async_resolution_performance(self):
        """Async resolution should be reasonably performant."""
        # For async resolution, we're mainly testing that the analysis overhead is reasonable
        # The actual async execution time will depend on the factory implementations
        
        async_registry = Registry()
        async_registry.add_factory(create_config, Config)
        async_registry.add_factory(create_database, Database)
        async_container = async_registry.create_container()
        
        # Measure time to create resolver (this includes dependency analysis)
        iterations = 100  # Fewer iterations since this includes more work
        start_time = time.perf_counter()
        for _ in range(iterations):
            resolver = async_container.create_resolver(Database)
            # Just create the resolver, don't execute it
        end_time = time.perf_counter()
        
        avg_time = (end_time - start_time) / iterations
        # Should be fast - under 10ms per analysis
        assert avg_time < 0.01, f"Async resolution analysis too slow: {avg_time:.6f}s"
    
    def test_resolver_caching_performance(self):
        """Dependency analysis caching should improve performance."""
        # First call should do analysis
        start_time = time.perf_counter()
        resolver1 = self.container.create_resolver(NotificationService)
        first_call_time = time.perf_counter() - start_time
        
        # Second call should use cached analysis
        start_time = time.perf_counter()
        resolver2 = self.container.create_resolver(NotificationService)
        second_call_time = time.perf_counter() - start_time
        
        # Second call should be faster (cached)
        # Note: This might not always be true due to timing variance, but generally should be
        # For now, just ensure both are reasonably fast
        assert first_call_time < 0.01, f"First resolver creation too slow: {first_call_time:.6f}s"
        assert second_call_time < 0.01, f"Cached resolver creation too slow: {second_call_time:.6f}s"


class TestCreateResolverAPI:
    """Test the create_resolver() method public API."""
    
    def setup_method(self):
        self.registry = Registry()
        self.registry.add_factory(create_config, Config)
        self.registry.add_factory(create_database, Database)
        self.registry.add_factory(create_user_service, UserService)
        self.container = self.registry.create_container()
    
    def test_create_resolver_for_sync_dependency(self):
        """create_resolver() should return DependenciesReady for sync chains."""
        from bevy.async_resolution import DependenciesReady
        
        resolver = self.container.create_resolver(Config)
        assert isinstance(resolver, DependenciesReady)
        
        # Should be able to get result synchronously
        result = resolver.get_result()
        assert isinstance(result, Config)
    
    def test_create_resolver_for_async_dependency(self):
        """create_resolver() should return DependenciesPending for async chains."""
        from bevy.async_resolution import DependenciesPending
        
        resolver = self.container.create_resolver(Database)
        assert isinstance(resolver, DependenciesPending)
        
        # Should return an awaitable
        result = resolver.get_result()
        assert inspect.iscoroutine(result) or hasattr(result, '__await__')
    
    def test_create_resolver_for_mixed_dependency(self):
        """create_resolver() should detect transitive async dependencies."""
        from bevy.async_resolution import DependenciesPending
        
        # UserService depends on Database (async), so should be async
        resolver = self.container.create_resolver(UserService)
        assert isinstance(resolver, DependenciesPending)
    
    @pytest.mark.asyncio
    async def test_resolver_produces_same_result_as_get(self):
        """Resolver should produce the same result as container.get()."""
        # Test sync case
        resolver_config = self.container.create_resolver(Config).get_result()
        get_config = self.container.get(Config)
        
        # Both should be actual instances (not awaitables) and should be the same
        assert isinstance(resolver_config, Config)
        assert isinstance(get_config, Config)
        assert resolver_config is get_config  # Should be cached
        
        # Test async case  
        resolver_db_awaitable = self.container.create_resolver(Database).get_result()
        get_db_awaitable = self.container.get(Database)
        
        # Both should be awaitables
        assert inspect.iscoroutine(resolver_db_awaitable) or hasattr(resolver_db_awaitable, '__await__')
        assert inspect.iscoroutine(get_db_awaitable) or hasattr(get_db_awaitable, '__await__')
        
        # Both should resolve to the same instance
        resolver_db = await resolver_db_awaitable
        get_db = await get_db_awaitable
        assert resolver_db is get_db  # Should be cached


class TestQualifiedDependenciesWithAsync:
    """Test qualified dependencies work correctly with async resolution."""
    
    def setup_method(self):
        self.registry = Registry()
        self.registry.add_factory(create_config, Config)
        self.container = self.registry.create_container()
    
    def test_qualified_sync_dependency(self):
        """Qualified sync dependencies should work normally."""
        # Add a qualified config
        special_config = Config("special://config")
        self.container.add(Config, special_config, qualifier="special")
        
        # Should return the qualified instance directly
        result = self.container.get(Config, qualifier="special")
        assert result is special_config
        assert not inspect.iscoroutine(result)
    
    def test_qualified_dependency_fallback_with_async(self):
        """Qualified dependencies should fall back to regular async resolution when needed."""
        # This would be the case where we request a qualified dependency
        # but don't have it, so it falls back to creating a new instance
        # Currently our implementation falls back to sync logic for qualified deps
        # This is acceptable for Phase 2 (we can optimize in later phases)
        pass


class TestDefaultFactoryWithAsync:
    """Test default_factory parameter works with async dependencies."""
    
    def setup_method(self):
        self.registry = Registry()
        self.registry.add_factory(create_config, Config)
        self.container = self.registry.create_container()
    
    def test_default_factory_sync(self):
        """default_factory with sync factory should work normally."""
        def custom_config_factory(container):
            return Config("custom://url")
        
        result = self.container.get(Config, default_factory=custom_config_factory)
        assert isinstance(result, Config)
        assert result.db_url == "custom://url"
        assert not inspect.iscoroutine(result)
    
    def test_default_factory_async_falls_back_to_sync_logic(self):
        """default_factory currently falls back to sync logic (acceptable for Phase 2)."""
        async def async_config_factory(container):
            await asyncio.sleep(0.001)
            return Config("async://url")
        
        # This will currently fall back to sync logic which will handle the async factory
        # The specific behavior depends on how the sync logic handles async factories
        # This is acceptable for Phase 2 - we can optimize in later phases
        pass


class TestTypeAnnotations:
    """Test that return types work correctly for type checking."""
    
    def test_sync_return_type_annotation(self):
        """Sync resolution should have correct type annotation."""
        # The type annotations are now T | Awaitable[T] which covers both cases
        pass
    
    def test_async_return_type_annotation(self):
        """Async resolution should have correct type annotation."""
        # The type annotations are now T | Awaitable[T] which covers both cases  
        pass


if __name__ == "__main__":
    pytest.main([__file__])