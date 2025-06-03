#!/usr/bin/env python3
"""
Comprehensive test suite for edge cases and missing coverage areas.

This test suite addresses gaps identified in the original test analysis:
- Factory caching edge cases
- Complex type scenarios  
- Error handling validation
- Container branching edge cases
- Thread safety (basic scenarios)
- Performance with larger dependency graphs
"""

import pytest
import threading
import time
from typing import List, Callable, Optional
from unittest.mock import Mock

from bevy import (
    injectable, auto_inject, Inject, Options, 
    InjectionStrategy, TypeMatchingStrategy,
    Container, Registry, get_container,
    DependencyResolutionError
)
from bevy.bundled.type_factory_hook import type_factory
from bevy.context_vars import global_container


# Test services for complex scenarios
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


class EmailService:
    def __init__(self, config: dict = None):
        self.config = config or {"smtp_host": "localhost"}
    
    def send(self, to: str, message: str):
        return f"Sent '{message}' to {to} via {self.config['smtp_host']}"


class CacheService:
    def __init__(self, ttl: int = 300):
        self.ttl = ttl
        self.data = {}
    
    def get(self, key: str):
        return self.data.get(key)
    
    def set(self, key: str, value: str):
        self.data[key] = value


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


class TestComplexTypeScenarios:
    """Test complex type annotations and edge cases."""
    
    def test_optional_type_with_none_value(self):
        """Test that Optional[T] can receive None values."""
        registry = Registry()
        container = Container(registry)
        
        @injectable
        def handle_optional_cache(
            cache: Inject[CacheService | None],
            message: str
        ):
            if cache is None:
                return f"No cache: {message}"
            return f"With cache: {message}"
        
        # No CacheService in container - should inject None
        result = container.call(handle_optional_cache, message="test")
        assert result == "No cache: test"
    
    def test_union_type_resolution_priority(self):
        """Test resolution priority with union types."""
        registry = Registry()
        type_factory.register_hook(registry)
        container = Container(registry)
        
        # Add specific instance
        container.add(EmailService({"smtp_host": "custom.smtp"}))
        
        @injectable
        def handle_union_service(
            service: Inject[EmailService | CacheService],
            message: str
        ):
            if isinstance(service, EmailService):
                return f"Email: {service.config['smtp_host']}"
            elif isinstance(service, CacheService):
                return f"Cache: {service.ttl}"
            return "Unknown service"
        
        result = container.call(handle_union_service, message="test")
        assert result == "Email: custom.smtp"
    
    def test_generic_type_handling(self):
        """Test handling of generic types like List[T]."""
        registry = Registry()
        container = Container(registry)
        
        # This should work with current implementation
        def create_db_list():
            return [
                DatabaseConnection("db1"),
                DatabaseConnection("db2")
            ]
        
        @injectable
        def handle_db_list(
            dbs: Inject[List[DatabaseConnection], Options(default_factory=create_db_list)]
        ):
            return [db.url for db in dbs]
        
        result = container.call(handle_db_list)
        assert result == ["db1", "db2"]
    
    def test_callable_type_injection(self):
        """Test injection of callable dependencies."""
        registry = Registry()
        container = Container(registry)
        
        def email_validator(email: str) -> bool:
            return "@" in email and "." in email
        
        container.add(Callable[[str], bool], email_validator)
        
        @injectable
        def validate_email(
            validator: Inject[Callable[[str], bool]],
            email: str
        ):
            return validator(email)
        
        result = container.call(validate_email, email="test@example.com")
        assert result is True
        
        result = container.call(validate_email, email="invalid-email")
        assert result is False


class TestErrorHandlingValidation:
    """Test comprehensive error handling scenarios."""
    
    def test_missing_dependency_error_message(self):
        """Test that missing dependency errors have helpful messages."""
        registry = Registry()
        container = Container(registry)
        
        @injectable
        def need_missing_service(service: Inject[UserRepository]):
            return service.find_user("123")
        
        with pytest.raises(DependencyResolutionError) as exc_info:
            container.call(need_missing_service)
        
        error = exc_info.value
        assert "UserRepository" in str(error)
        assert "service" in str(error)  # parameter name
    
    def test_qualified_dependency_not_found_error(self):
        """Test error message for missing qualified dependencies."""
        registry = Registry()
        container = Container(registry)
        
        # Add unqualified instance but not qualified one
        container.add(DatabaseConnection("default"))
        
        @injectable
        def need_qualified_db(
            db: Inject[DatabaseConnection, Options(qualifier="primary")]
        ):
            return db.url
        
        with pytest.raises(DependencyResolutionError) as exc_info:
            container.call(need_qualified_db)
        
        error = exc_info.value
        assert "qualifier" in str(error).lower()
        assert "primary" in str(error)
    
    def test_factory_error_propagation(self):
        """Test that factory errors are properly propagated."""
        registry = Registry()
        container = Container(registry)
        
        def failing_factory():
            raise ValueError("Factory failed!")
        
        @injectable
        def use_failing_factory(
            service: Inject[UserRepository, Options(default_factory=failing_factory)]
        ):
            return service.find_user("123")
        
        with pytest.raises(ValueError, match="Factory failed!"):
            container.call(use_failing_factory)
    
    def test_strict_vs_non_strict_mode_behavior(self):
        """Test the difference between strict and non-strict modes."""
        registry = Registry()
        container = Container(registry)
        
        @injectable(strict=True)
        def strict_function(service: Inject[UserRepository]):
            return service.find_user("123") if service else "No service"
        
        @injectable(strict=False)
        def non_strict_function(service: Inject[UserRepository]):
            return service.find_user("123") if service else "No service"
        
        # Strict mode should raise error
        with pytest.raises(DependencyResolutionError):
            container.call(strict_function)
        
        # Non-strict mode should inject None
        result = container.call(non_strict_function)
        assert result == "No service"


class TestContainerBranchingEdgeCases:
    """Test complex container branching scenarios."""
    
    def test_deep_container_inheritance_chain(self):
        """Test behavior with multiple levels of container inheritance."""
        registry = Registry()
        type_factory.register_hook(registry)
        
        # Create inheritance chain: grandparent -> parent -> child
        grandparent = Container(registry)
        grandparent.add(DatabaseConnection("grandparent-db"))
        
        parent = grandparent.branch()
        parent.add(EmailService({"smtp_host": "parent.smtp"}))
        
        child = parent.branch()
        child.add(CacheService(ttl=600))
        
        @injectable
        def use_all_services(
            db: Inject[DatabaseConnection],
            email: Inject[EmailService],
            cache: Inject[CacheService]
        ):
            return f"DB: {db.url}, Email: {email.config['smtp_host']}, Cache: {cache.ttl}"
        
        result = child.call(use_all_services)
        assert "grandparent-db" in result
        assert "parent.smtp" in result
        assert "600" in result
    
    def test_qualified_instance_inheritance(self):
        """Test how qualified instances are inherited in container chains."""
        registry = Registry()
        parent = Container(registry)
        
        # Add qualified instances to parent
        parent.add(DatabaseConnection, DatabaseConnection("parent-primary"), qualifier="primary")
        parent.add(DatabaseConnection, DatabaseConnection("parent-backup"), qualifier="backup")
        
        child = parent.branch()
        # Override only the primary in child
        child.add(DatabaseConnection, DatabaseConnection("child-primary"), qualifier="primary")
        
        @injectable
        def use_qualified_dbs(
            primary: Inject[DatabaseConnection, Options(qualifier="primary")],
            backup: Inject[DatabaseConnection, Options(qualifier="backup")]
        ):
            return f"Primary: {primary.url}, Backup: {backup.url}"
        
        result = child.call(use_qualified_dbs)
        assert "child-primary" in result  # Overridden in child
        assert "parent-backup" in result  # Inherited from parent
    
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


class TestConcurrencyBasics:
    """Basic tests for thread safety and concurrent access."""
    
    def test_concurrent_container_access(self):
        """Test that multiple threads can safely access the same container."""
        registry = Registry()
        type_factory.register_hook(registry)
        container = Container(registry)
        
        results = []
        errors = []
        
        @injectable
        def get_service(service: Inject[DatabaseConnection]):
            # Simulate some work
            time.sleep(0.01)
            return service.url
        
        def worker():
            try:
                result = container.call(get_service)
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = [threading.Thread(target=worker) for _ in range(10)]
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Verify results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 10
        # All results should be the same (singleton behavior)
        assert all(result == results[0] for result in results)
    
    def test_global_container_thread_isolation(self):
        """Test that global container context is properly isolated."""
        # Reset global context
        token = global_container.set(None)
        try:
            container1 = get_container()
            type_factory.register_hook(container1.registry)
            container1.add(DatabaseConnection("thread1-db"))
            
            container2_ref = []
            error_ref = []
            
            def setup_thread2():
                try:
                    # This thread should get its own container
                    container2 = get_container()
                    type_factory.register_hook(container2.registry)
                    container2.add(DatabaseConnection("thread2-db"))
                    container2_ref.append(container2)
                except Exception as e:
                    error_ref.append(e)
            
            thread = threading.Thread(target=setup_thread2)
            thread.start()
            thread.join()
            
            assert len(error_ref) == 0, f"Thread 2 failed: {error_ref}"
            assert len(container2_ref) == 1
            
            # Containers should be different
            container2 = container2_ref[0]
            assert container1 is not container2
            
            # Each should have their own instance
            db1 = container1.get(DatabaseConnection)
            db2 = container2.get(DatabaseConnection)
            assert db1.url == "thread1-db"
            assert db2.url == "thread2-db"
            
        finally:
            global_container.reset(token)


class TestPerformanceBasics:
    """Basic performance tests for larger dependency graphs."""
    
    def test_large_dependency_count(self):
        """Test performance with many dependencies."""
        registry = Registry()
        type_factory.register_hook(registry)
        container = Container(registry)
        
        # Create 50 different service types
        service_types = []
        for i in range(50):
            service_class = type(f"Service{i}", (), {
                "__init__": lambda self, value=i: setattr(self, "value", value)
            })
            service_types.append(service_class)
            container.add(service_class())
        
        # Create a function that depends on all of them
        annotations = {f"service_{i}": Inject[service_types[i]] for i in range(50)}
        
        @injectable
        def use_many_services(**services):
            return sum(service.value for service in services.values())
        
        # Manually set annotations (since we can't dynamically create parameter list)
        use_many_services.__annotations__ = annotations
        
        start_time = time.time()
        result = container.call(use_many_services)
        end_time = time.time()
        
        # Should complete reasonably quickly (under 1 second)
        assert end_time - start_time < 1.0
        assert result == sum(range(50))
    
    def test_nested_dependency_resolution(self):
        """Test performance with nested dependency chains."""
        registry = Registry()
        type_factory.register_hook(registry)
        container = Container(registry)
        
        # Create a chain: A -> B -> C -> D -> E
        class ServiceE:
            def __init__(self):
                self.name = "E"
        
        class ServiceD:
            def __init__(self, e: ServiceE):
                self.e = e
                self.name = "D"
        
        class ServiceC:
            def __init__(self, d: ServiceD):
                self.d = d
                self.name = "C"
        
        class ServiceB:
            def __init__(self, c: ServiceC):
                self.c = c
                self.name = "B"
        
        class ServiceA:
            def __init__(self, b: ServiceB):
                self.b = b
                self.name = "A"
        
        @injectable
        def use_nested_service(service: Inject[ServiceA]):
            return f"{service.name}->{service.b.name}->{service.b.c.name}->{service.b.c.d.name}->{service.b.c.d.e.name}"
        
        start_time = time.time()
        result = container.call(use_nested_service)
        end_time = time.time()
        
        # Should complete quickly and return correct chain
        assert end_time - start_time < 0.1
        assert result == "A->B->C->D->E"


class TestAnnotationEdgeCases:
    """Test edge cases with type annotations and metadata."""
    
    def test_malformed_inject_annotation(self):
        """Test behavior with malformed Inject annotations."""
        registry = Registry()
        container = Container(registry)
        
        # This should not break the system
        @injectable
        def bad_annotation(service: "Inject[NonExistentClass]"):  # String annotation
            return str(service)
        
        # Should handle gracefully (may raise error or inject None depending on strict mode)
        with pytest.raises((DependencyResolutionError, NameError)):
            container.call(bad_annotation)
    
    def test_circular_reference_detection(self):
        """Test detection of circular dependencies."""
        registry = Registry()
        type_factory.register_hook(registry)
        container = Container(registry)
        
        # This will create a circular dependency via constructor injection
        class CircularA:
            def __init__(self, b: 'CircularB'):
                self.b = b
        
        class CircularB:
            def __init__(self, a: CircularA):
                self.a = a
        
        @injectable
        def use_circular(service: Inject[CircularA]):
            return service.b.a.b.a  # Should not get here
        
        # This should either detect the circular dependency or fail gracefully
        with pytest.raises((RecursionError, DependencyResolutionError)):
            container.call(use_circular)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])