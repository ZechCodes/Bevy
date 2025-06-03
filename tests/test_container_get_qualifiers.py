#!/usr/bin/env python3
"""
Tests for container.get with qualifier support to ensure feature parity with Inject.
"""

import pytest
from bevy import Container, injectable, Inject
from bevy.registries import Registry
from bevy.injection_types import Options, DependencyResolutionError


class DatabaseConnection:
    def __init__(self, url="default"):
        self.url = url


class TestContainerGetWithQualifiers:
    """Test container.get with qualifier parameter."""
    
    def test_get_with_qualifier_basic(self):
        """Test basic qualified instance retrieval."""
        registry = Registry()
        container = Container(registry)
        
        # Add qualified instances
        container.add(DatabaseConnection, DatabaseConnection("primary"), qualifier="primary")
        container.add(DatabaseConnection, DatabaseConnection("backup"), qualifier="backup")
        
        # Retrieve by qualifier
        primary = container.get(DatabaseConnection, qualifier="primary")
        backup = container.get(DatabaseConnection, qualifier="backup")
        
        assert primary.url == "primary"
        assert backup.url == "backup"
    
    def test_get_qualified_vs_unqualified(self):
        """Test that qualified and unqualified instances are separate."""
        registry = Registry()
        container = Container(registry)
        
        # Add both qualified and unqualified
        container.add(DatabaseConnection("unqualified"))
        container.add(DatabaseConnection, DatabaseConnection("qualified"), qualifier="special")
        
        unqualified = container.get(DatabaseConnection)
        qualified = container.get(DatabaseConnection, qualifier="special")
        
        assert unqualified.url == "unqualified"
        assert qualified.url == "qualified"
        assert unqualified is not qualified
    
    def test_qualified_inheritance_from_parent(self):
        """Test that qualified instances are inherited from parent."""
        registry = Registry()
        parent = Container(registry)
        
        parent.add(DatabaseConnection, DatabaseConnection("parent-primary"), qualifier="primary")
        
        child = parent.branch()
        
        # Child should inherit qualified instance
        primary = child.get(DatabaseConnection, qualifier="primary")
        assert primary.url == "parent-primary"
    
    def test_qualified_override_in_child(self):
        """Test that child can override parent's qualified instances."""
        registry = Registry()
        parent = Container(registry)
        parent.add(DatabaseConnection, DatabaseConnection("parent-primary"), qualifier="primary")
        
        child = parent.branch()
        child.add(DatabaseConnection, DatabaseConnection("child-primary"), qualifier="primary")
        
        parent_primary = parent.get(DatabaseConnection, qualifier="primary")
        child_primary = child.get(DatabaseConnection, qualifier="primary")
        
        assert parent_primary.url == "parent-primary"
        assert child_primary.url == "child-primary"
    
    def test_qualified_sibling_isolation(self):
        """Test that sibling containers don't share qualified instances."""
        registry = Registry()
        parent = Container(registry)
        
        child1 = parent.branch()
        child2 = parent.branch()
        
        child1.add(DatabaseConnection, DatabaseConnection("child1-primary"), qualifier="primary")
        child2.add(DatabaseConnection, DatabaseConnection("child2-primary"), qualifier="primary")
        
        primary1 = child1.get(DatabaseConnection, qualifier="primary")
        primary2 = child2.get(DatabaseConnection, qualifier="primary")
        
        assert primary1.url == "child1-primary"
        assert primary2.url == "child2-primary"
    
    def test_qualified_with_default_factory(self):
        """Test qualified instances with default factories."""
        registry = Registry()
        container = Container(registry)
        
        def primary_factory():
            return DatabaseConnection("factory-primary")
        
        # Should use factory when qualified instance doesn't exist
        primary = container.get(DatabaseConnection, qualifier="primary", default_factory=primary_factory)
        assert primary.url == "factory-primary"
        
        # Should be cached for future requests
        primary2 = container.get(DatabaseConnection, qualifier="primary", default_factory=primary_factory)
        assert primary is primary2
    
    def test_qualified_error_when_not_found(self):
        """Test error when qualified instance is not found."""
        registry = Registry()
        container = Container(registry)
        
        with pytest.raises(DependencyResolutionError, match="Cannot resolve qualified dependency"):
            container.get(DatabaseConnection, qualifier="nonexistent")


class TestContainerGetVsInjectQualifierBehavior:
    """Test that container.get and Inject have identical behavior with qualifiers."""
    
    def test_qualified_resolution_identical(self):
        """Test that qualified resolution is identical."""
        registry = Registry()
        container = Container(registry)
        
        container.add(DatabaseConnection, DatabaseConnection("primary-db"), qualifier="primary")
        
        # Both should return the same qualified instance
        result1 = container.get(DatabaseConnection, qualifier="primary")
        
        @injectable
        def get_primary(db: Inject[DatabaseConnection, Options(qualifier="primary")]):
            return db
        
        result2 = container.call(get_primary)
        
        assert result1.url == "primary-db"
        assert result2.url == "primary-db"
        assert result1 is result2
    
    def test_qualified_inheritance_identical(self):
        """Test qualified inheritance behavior is identical."""
        registry = Registry()
        parent = Container(registry)
        parent.add(DatabaseConnection, DatabaseConnection("parent-backup"), qualifier="backup")
        
        child = parent.branch()
        
        result1 = child.get(DatabaseConnection, qualifier="backup")
        
        @injectable
        def get_backup(db: Inject[DatabaseConnection, Options(qualifier="backup")]):
            return db
        
        result2 = child.call(get_backup)
        
        assert result1.url == "parent-backup"
        assert result2.url == "parent-backup"
        assert result1 is result2
    
    def test_qualified_with_factory_identical(self):
        """Test qualified instances with factories are identical."""
        registry = Registry()
        container = Container(registry)
        
        def factory():
            return DatabaseConnection("qualified-factory")
        
        result1 = container.get(DatabaseConnection, qualifier="cache", default_factory=factory)
        
        @injectable
        def get_cache(db: Inject[DatabaseConnection, Options(qualifier="cache", default_factory=factory)]):
            return db
        
        result2 = container.call(get_cache)
        
        assert result1.url == "qualified-factory"
        assert result2.url == "qualified-factory"
        assert result1 is result2
    
    def test_qualified_error_conditions_identical(self):
        """Test that qualified error conditions are identical."""
        registry = Registry()
        container = Container(registry)
        
        # Both should fail the same way for missing qualified instances
        with pytest.raises(DependencyResolutionError):
            container.get(DatabaseConnection, qualifier="missing")
        
        @injectable
        def get_missing(db: Inject[DatabaseConnection, Options(qualifier="missing")]):
            return db
        
        with pytest.raises(DependencyResolutionError):
            container.call(get_missing)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])