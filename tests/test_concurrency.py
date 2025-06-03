#!/usr/bin/env python3
"""
Tests for concurrency and thread safety.

This test suite covers basic concurrency scenarios including:
- Concurrent container access
- Global container thread isolation
- Thread-safe dependency injection
- Race condition prevention
"""

import pytest
import threading
import time
from bevy import injectable, Inject, Container, get_container
from bevy.bundled.type_factory_hook import type_factory
from bevy.context_vars import global_container
from bevy.registries import Registry


# Test services for concurrency scenarios
class DatabaseConnection:
    def __init__(self, url: str = "sqlite://test.db"):
        self.url = url
        self.thread_id = threading.get_ident()


class UserService:
    def __init__(self, name: str = "UserService"):
        self.name = name
        self.thread_id = threading.get_ident()


class TestConcurrentContainerAccess:
    """Test concurrent access to the same container."""
    
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
    
    def test_concurrent_instance_creation(self):
        """Test concurrent creation of instances."""
        registry = Registry()
        type_factory.register_hook(registry)
        container = Container(registry)
        
        creation_count = 0
        creation_lock = threading.Lock()
        
        class CountingService:
            def __init__(self):
                nonlocal creation_count
                with creation_lock:
                    creation_count += 1
                    self.instance_id = creation_count
                time.sleep(0.001)  # Simulate creation work
        
        results = []
        errors = []
        
        @injectable
        def get_counting_service(service: Inject[CountingService]):
            return service.instance_id
        
        def worker():
            try:
                result = container.call(get_counting_service)
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Create many threads to stress test
        threads = [threading.Thread(target=worker) for _ in range(20)]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Should only create one instance despite concurrent access
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 20
        assert all(result == 1 for result in results), f"Expected all 1s, got: {set(results)}"
        assert creation_count == 1, f"Expected 1 creation, got {creation_count}"
    
    def test_concurrent_different_services(self):
        """Test concurrent access to different services."""
        registry = Registry()
        type_factory.register_hook(registry)
        container = Container(registry)
        
        db_results = []
        user_results = []
        errors = []
        
        @injectable
        def get_db(service: Inject[DatabaseConnection]):
            time.sleep(0.005)  # Simulate work
            return service.url
        
        @injectable
        def get_user(service: Inject[UserService]):
            time.sleep(0.005)  # Simulate work
            return service.name
        
        def db_worker():
            try:
                result = container.call(get_db)
                db_results.append(result)
            except Exception as e:
                errors.append(e)
        
        def user_worker():
            try:
                result = container.call(get_user)
                user_results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Mix of different service workers
        threads = []
        for _ in range(5):
            threads.append(threading.Thread(target=db_worker))
            threads.append(threading.Thread(target=user_worker))
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(db_results) == 5
        assert len(user_results) == 5
        assert all(result == "sqlite://test.db" for result in db_results)
        assert all(result == "UserService" for result in user_results)


class TestGlobalContainerThreadIsolation:
    """Test thread isolation with global container."""
    
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
    
    def test_context_variable_inheritance(self):
        """Test that context variables are properly inherited by child threads."""
        registry = Registry()
        type_factory.register_hook(registry)
        parent_container = Container(registry)
        parent_container.add(UserService("parent-service"))
        
        # Set parent container in context
        token = global_container.set(parent_container)
        try:
            child_results = []
            errors = []
            
            @injectable
            def get_service_name(service: Inject[UserService]):
                return service.name
            
            def child_thread_work():
                try:
                    # Child thread should inherit parent's context
                    child_container = get_container()
                    result = child_container.call(get_service_name)
                    child_results.append(result)
                except Exception as e:
                    errors.append(e)
            
            thread = threading.Thread(target=child_thread_work)
            thread.start()
            thread.join()
            
            assert len(errors) == 0, f"Child thread failed: {errors}"
            assert len(child_results) == 1
            assert child_results[0] == "parent-service"
            
        finally:
            global_container.reset(token)


class TestFactoryConcurrency:
    """Test factory behavior under concurrent access."""
    
    def test_concurrent_factory_calls(self):
        """Test that factory is called only once under concurrent access."""
        registry = Registry()
        container = Container(registry)
        
        factory_call_count = 0
        factory_lock = threading.Lock()
        
        def counting_factory():
            nonlocal factory_call_count
            with factory_lock:
                factory_call_count += 1
                current_count = factory_call_count
            time.sleep(0.01)  # Simulate factory work
            return DatabaseConnection(f"factory-{current_count}")
        
        results = []
        errors = []
        
        @injectable
        def get_factory_db(db: Inject[DatabaseConnection, Options(default_factory=counting_factory)]):
            return db.url
        
        def worker():
            try:
                result = container.call(get_factory_db)
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Many concurrent threads using same factory
        threads = [threading.Thread(target=worker) for _ in range(15)]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 15
        # Factory should only be called once, all should get same result
        assert factory_call_count == 1, f"Expected 1 factory call, got {factory_call_count}"
        assert all(result == "factory-1" for result in results)
    
    def test_concurrent_uncached_factory_calls(self):
        """Test uncached factory behavior under concurrent access."""
        registry = Registry()
        container = Container(registry)
        
        factory_call_count = 0
        factory_lock = threading.Lock()
        
        def counting_factory():
            nonlocal factory_call_count
            with factory_lock:
                factory_call_count += 1
                current_count = factory_call_count
            time.sleep(0.001)  # Simulate factory work
            return DatabaseConnection(f"uncached-{current_count}")
        
        results = []
        errors = []
        
        @injectable
        def get_uncached_db(db: Inject[DatabaseConnection, Options(
            default_factory=counting_factory,
            cache_factory_result=False
        )]):
            return db.url
        
        def worker():
            try:
                result = container.call(get_uncached_db)
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Multiple threads, each should get fresh instance
        threads = [threading.Thread(target=worker) for _ in range(8)]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 8
        # Each call should create a new instance
        assert factory_call_count == 8, f"Expected 8 factory calls, got {factory_call_count}"
        # All results should be different
        assert len(set(results)) == 8, f"Expected 8 unique results, got: {results}"


class TestContainerBranchingConcurrency:
    """Test concurrent container branching scenarios."""
    
    def test_concurrent_container_branching(self):
        """Test that concurrent container branching is safe."""
        registry = Registry()
        type_factory.register_hook(registry)
        parent = Container(registry)
        parent.add(DatabaseConnection("parent-db"))
        
        child_containers = []
        errors = []
        
        def create_child_container():
            try:
                child = parent.branch()
                child.add(UserService(f"child-{threading.get_ident()}"))
                child_containers.append(child)
            except Exception as e:
                errors.append(e)
        
        # Create multiple child containers concurrently
        threads = [threading.Thread(target=create_child_container) for _ in range(10)]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(child_containers) == 10
        
        # Each child should have access to parent's database
        for child in child_containers:
            db = child.get(DatabaseConnection)
            assert db.url == "parent-db"
            
            # Each should have its own user service
            user = child.get(UserService)
            assert "child-" in user.name
        
        # All user services should be unique
        user_names = [child.get(UserService).name for child in child_containers]
        assert len(set(user_names)) == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])