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
        # This test will be implemented when circular detection is added
        pass
    
    def test_async_circular_dependency_detection(self):
        """Should detect circular dependencies involving async factories."""
        # This test will be implemented when circular detection is added
        pass
    
    def test_mixed_circular_dependency_detection(self):
        """Should detect circular dependencies in mixed sync/async chains."""
        # This test will be implemented when circular detection is added
        pass


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
    
    def test_sync_path_no_async_overhead(self):
        """Sync-only paths should have minimal async overhead."""
        # Detailed performance testing will be implemented
        pass
    
    def test_async_resolution_performance(self):
        """Async resolution should be reasonably performant.""" 
        # Performance benchmarks will be implemented
        pass


class TestTypeAnnotations:
    """Test that return types work correctly for type checking."""
    
    def test_sync_return_type_annotation(self):
        """Sync resolution should have correct type annotation."""
        # Type checking tests will be implemented when resolver classes are added
        pass
    
    def test_async_return_type_annotation(self):
        """Async resolution should have correct type annotation."""
        # Type checking tests will be implemented when resolver classes are added
        pass


if __name__ == "__main__":
    pytest.main([__file__])