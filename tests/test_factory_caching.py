#!/usr/bin/env python3
"""
Tests for factory-based caching functionality.

This test suite covers factory caching behavior including:
- Factory caching with container dependencies
- Cache isolation across containers  
- Mixed cached and uncached factories
- Parent container cache inheritance
"""

import pytest
from bevy import injectable, Inject, Container, Registry
from bevy.injection_types import Options
from bevy.bundled.type_factory_hook import type_factory


# Test services for factory caching scenarios
class DatabaseConnection:
    def __init__(self, url: str = "sqlite://test.db"):
        self.url = url
        self.connected = False
    
    def connect(self):
        self.connected = True
        return f"Connected to {self.url}"


class UserRepository:
    def __init__(self, db: DatabaseConnection):
        self.db = db
    
    def find_user(self, user_id: str):
        return f"User {user_id} from {self.db.url}"


class TestFactoryCachingEdgeCases:
    """Test factory caching behavior in complex scenarios."""
    
    def test_factory_caching_with_container_dependencies(self):
        """Test that factories with dependencies are cached correctly."""
        registry = Registry()
        type_factory.register_hook(registry)
        container = Container(registry)
        
        # Add a base dependency
        container.add(DatabaseConnection("postgresql://prod"))
        
        call_count = 0
        
        def create_user_repo():
            nonlocal call_count
            call_count += 1
            # This factory depends on DatabaseConnection
            return UserRepository(DatabaseConnection("factory://created"))
        
        @injectable
        def service_a(repo: Inject[UserRepository, Options(default_factory=create_user_repo)]):
            return repo.find_user("123")
        
        @injectable
        def service_b(repo: Inject[UserRepository, Options(default_factory=create_user_repo)]):
            return repo.find_user("456")
        
        # Both should use the same factory-created instance
        result1 = container.call(service_a)
        result2 = container.call(service_b)
        
        assert call_count == 1, "Factory should only be called once"
        assert "factory://created" in result1
        assert "factory://created" in result2
    
    def test_factory_cache_isolation_across_containers(self):
        """Test that factory caches are isolated between containers."""
        registry = Registry()
        container1 = Container(registry)
        container2 = Container(registry)
        
        call_count = 0
        
        def counting_factory():
            nonlocal call_count
            call_count += 1
            return DatabaseConnection(f"db-{call_count}")
        
        @injectable
        def get_db(db: Inject[DatabaseConnection, Options(default_factory=counting_factory)]):
            return db.url
        
        # Each container should have its own cache
        result1 = container1.call(get_db)
        result2 = container2.call(get_db)
        
        assert call_count == 2, "Factory should be called once per container"
        assert result1 == "db-1"
        assert result2 == "db-2"
    
    def test_factory_cache_disabled_creates_fresh_instances(self):
        """Test that cache_factory_result=False creates fresh instances."""
        registry = Registry()
        container = Container(registry)
        
        call_count = 0
        
        def counting_factory():
            nonlocal call_count
            call_count += 1
            return DatabaseConnection(f"fresh-{call_count}")
        
        @injectable
        def service_a(db: Inject[DatabaseConnection, Options(
            default_factory=counting_factory,
            cache_factory_result=False
        )]):
            return db.url
        
        @injectable
        def service_b(db: Inject[DatabaseConnection, Options(
            default_factory=counting_factory,
            cache_factory_result=False
        )]):
            return db.url
        
        # Each call should create a fresh instance
        result1 = container.call(service_a)
        result2 = container.call(service_b)
        
        assert call_count == 2, "Factory should be called for each service"
        assert result1 == "fresh-1"
        assert result2 == "fresh-2"
    
    def test_mixed_cached_and_uncached_factories(self):
        """Test mixing cached and uncached factories for the same type."""
        registry = Registry()
        container = Container(registry)
        
        call_count = 0
        
        def counting_factory():
            nonlocal call_count
            call_count += 1
            return DatabaseConnection(f"mixed-{call_count}")
        
        @injectable
        def cached_service(db: Inject[DatabaseConnection, Options(
            default_factory=counting_factory,
            cache_factory_result=True  # Explicitly enable caching
        )]):
            return db.url
        
        @injectable
        def uncached_service(db: Inject[DatabaseConnection, Options(
            default_factory=counting_factory,
            cache_factory_result=False
        )]):
            return db.url
        
        # Cached service should create and store instance
        result1 = container.call(cached_service)
        assert call_count == 1
        assert result1 == "mixed-1"
        
        # Second cached call should reuse instance
        result2 = container.call(cached_service)
        assert call_count == 1  # No additional factory call
        assert result2 == "mixed-1"
        
        # Uncached service should create fresh instance
        result3 = container.call(uncached_service)
        assert call_count == 2  # New factory call
        assert result3 == "mixed-2"
    
    def test_factory_cache_inheritance(self):
        """Test that factory caches are properly inherited."""
        registry = Registry()
        parent = Container(registry)
        
        call_count = 0
        
        def counting_factory():
            nonlocal call_count
            call_count += 1
            return DatabaseConnection(f"factory-{call_count}")
        
        @injectable
        def get_db(db: Inject[DatabaseConnection, Options(default_factory=counting_factory)]):
            return db.url
        
        # Create instance in parent
        parent_result = parent.call(get_db)
        assert call_count == 1
        assert parent_result == "factory-1"
        
        # Child should inherit cached instance
        child = parent.branch()
        child_result = child.call(get_db)
        assert call_count == 1  # No additional factory call
        assert child_result == "factory-1"  # Same instance


class TestFactoryWithDependencyInjection:
    """Test factories that themselves require dependency injection."""
    
    def test_factory_with_injected_dependencies(self):
        """Test that factories can have their own dependencies injected."""
        registry = Registry()
        type_factory.register_hook(registry)
        container = Container(registry)
        
        # Add base service that factory will depend on
        base_db = DatabaseConnection("base://connection")
        container.add(base_db)
        
        @injectable
        def create_repository(db: Inject[DatabaseConnection]) -> UserRepository:
            """Factory that depends on injected DatabaseConnection."""
            return UserRepository(db)
        
        @injectable
        def service_function(repo: Inject[UserRepository, Options(default_factory=create_repository)]):
            return repo.find_user("test")
        
        result = container.call(service_function)
        assert "base://connection" in result
        assert "User test" in result
    
    def test_nested_factory_dependencies(self):
        """Test factories that create objects with their own factory dependencies."""
        registry = Registry()
        type_factory.register_hook(registry)
        container = Container(registry)
        
        call_count = 0
        
        def db_factory():
            nonlocal call_count
            call_count += 1
            return DatabaseConnection(f"nested-{call_count}")
        
        @injectable
        def repo_factory(db: Inject[DatabaseConnection, Options(default_factory=db_factory)]):
            return UserRepository(db)
        
        @injectable
        def service_a(repo: Inject[UserRepository, Options(default_factory=repo_factory)]):
            return repo.find_user("a")
        
        @injectable
        def service_b(repo: Inject[UserRepository, Options(default_factory=repo_factory)]):
            return repo.find_user("b")
        
        # Both services should share the same repository (and thus the same db)
        result_a = container.call(service_a)
        result_b = container.call(service_b)
        
        assert call_count == 1, "Database factory should only be called once"
        assert "nested-1" in result_a
        assert "nested-1" in result_b


if __name__ == "__main__":
    pytest.main([__file__, "-v"])