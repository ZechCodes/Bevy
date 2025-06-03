#!/usr/bin/env python3
"""
Comprehensive tests for container.get to ensure feature parity with Inject.

Tests cover:
1. container.get with default_factory
2. container.get vs Inject identical behavior  
3. container.get with qualifiers (once implemented)
4. Edge cases and error conditions
"""

import pytest
from bevy import Container, injectable, Inject
from bevy.registries import Registry
from bevy.injection_types import Options, DependencyResolutionError
from bevy.bundled.type_factory_hook import type_factory


class TestService:
    def __init__(self, value="default"):
        self.value = value


class DatabaseConnection:
    def __init__(self, url="default"):
        self.url = url


class TestContainerGetWithDefaultFactory:
    """Test container.get with default_factory parameter."""
    
    def test_get_with_default_factory_basic(self):
        """Test basic default_factory functionality."""
        registry = Registry()
        container = Container(registry)
        
        def factory():
            return TestService("factory-created")
        
        # Should use factory when type doesn't exist
        result = container.get(TestService, default_factory=factory)
        assert result.value == "factory-created"
    
    def test_get_with_default_factory_caching(self):
        """Test that default factory results are cached."""
        registry = Registry()
        container = Container(registry)
        
        call_count = 0
        def counting_factory():
            nonlocal call_count
            call_count += 1
            return TestService(f"factory-{call_count}")
        
        # First call should create instance
        result1 = container.get(TestService, default_factory=counting_factory)
        assert result1.value == "factory-1"
        assert call_count == 1
        
        # Second call should return cached instance
        result2 = container.get(TestService, default_factory=counting_factory)
        assert result2.value == "factory-1"
        assert result1 is result2
        assert call_count == 1  # No additional factory call
    
    def test_get_with_default_factory_inheritance(self):
        """Test factory cache inheritance from parent."""
        registry = Registry()
        parent = Container(registry)
        
        def factory():
            return TestService("parent-factory")
        
        # Create in parent
        parent_result = parent.get(TestService, default_factory=factory)
        
        # Child should inherit
        child = parent.branch()
        child_result = child.get(TestService, default_factory=factory)
        
        assert parent_result.value == "parent-factory"
        assert child_result.value == "parent-factory"
        assert parent_result is child_result
    
    def test_get_with_default_factory_sibling_isolation(self):
        """Test factory cache isolation between siblings."""
        registry = Registry()
        parent = Container(registry)
        
        call_count = 0
        def counting_factory():
            nonlocal call_count
            call_count += 1
            return TestService(f"sibling-{call_count}")
        
        child1 = parent.branch()
        child2 = parent.branch()
        
        result1 = child1.get(TestService, default_factory=counting_factory)
        result2 = child2.get(TestService, default_factory=counting_factory)
        
        assert call_count == 2
        assert result1.value == "sibling-1"
        assert result2.value == "sibling-2"
        assert result1 is not result2
    
    def test_get_with_default_factory_exception_propagation(self):
        """Test that factory exceptions are properly propagated."""
        registry = Registry()
        container = Container(registry)
        
        def failing_factory():
            raise ValueError("Factory failed")
        
        with pytest.raises(ValueError, match="Factory failed"):
            container.get(TestService, default_factory=failing_factory)


class TestContainerGetVsInjectBehavior:
    """Test that container.get and Inject have identical behavior."""
    
    def test_normal_resolution_identical(self):
        """Test that normal resolution is identical."""
        registry = Registry()
        type_factory.register_hook(registry)
        container = Container(registry)
        
        # Both should create the same instance via type factory
        result1 = container.get(TestService)
        
        @injectable
        def get_service(svc: Inject[TestService]):
            return svc
        
        result2 = container.call(get_service)
        
        assert result1.value == result2.value
        assert result1 is result2  # Should be cached
    
    def test_existing_instance_identical(self):
        """Test behavior with existing instances."""
        registry = Registry()
        container = Container(registry)
        
        # Add instance manually
        container.add(TestService("manual"))
        
        result1 = container.get(TestService)
        
        @injectable
        def get_service(svc: Inject[TestService]):
            return svc
        
        result2 = container.call(get_service)
        
        assert result1.value == "manual"
        assert result2.value == "manual"
        assert result1 is result2
    
    def test_default_factory_identical(self):
        """Test that default factory behavior is identical."""
        registry = Registry()
        container = Container(registry)
        
        def factory():
            return TestService("factory")
        
        result1 = container.get(TestService, default_factory=factory)
        
        @injectable
        def get_service(svc: Inject[TestService, Options(default_factory=factory)]):
            return svc
        
        result2 = container.call(get_service)
        
        assert result1.value == "factory"
        assert result2.value == "factory"
        assert result1 is result2  # Should be cached by factory key
    
    def test_parent_child_inheritance_identical(self):
        """Test parent-child inheritance behavior is identical."""
        registry = Registry()
        parent = Container(registry)
        parent.add(TestService("parent"))
        
        child = parent.branch()
        
        result1 = child.get(TestService)
        
        @injectable
        def get_service(svc: Inject[TestService]):
            return svc
        
        result2 = child.call(get_service)
        
        assert result1.value == "parent"
        assert result2.value == "parent"
        assert result1 is result2
    
    def test_error_conditions_identical(self):
        """Test that error conditions are identical."""
        registry = Registry()
        container = Container(registry)
        
        # Both should fail the same way for unresolvable types
        with pytest.raises(DependencyResolutionError):
            container.get(object)  # No factory for object
        
        @injectable
        def get_object(obj: Inject[object]):
            return obj
        
        with pytest.raises(DependencyResolutionError):
            container.call(get_object)


class TestContainerGetEdgeCases:
    """Test edge cases for container.get."""
    
    def test_get_with_default_and_default_factory(self):
        """Test behavior when both default and default_factory are provided."""
        registry = Registry()
        container = Container(registry)
        
        def factory():
            return TestService("factory")
        
        default_value = TestService("default")
        
        # Should prioritize default_factory over default when type doesn't exist
        result = container.get(TestService, default=default_value, default_factory=factory)
        assert result.value == "factory"
    
    def test_get_with_factory_that_needs_injection(self):
        """Test factory that requires dependency injection."""
        registry = Registry()
        type_factory.register_hook(registry)
        container = Container(registry)
        
        @injectable
        def factory_with_deps(db: Inject[DatabaseConnection]):
            return TestService(f"factory-with-{db.url}")
        
        result = container.get(TestService, default_factory=factory_with_deps)
        assert "factory-with-default" in result.value


if __name__ == "__main__":
    pytest.main([__file__, "-v"])