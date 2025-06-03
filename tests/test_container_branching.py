#!/usr/bin/env python3
"""
Tests for container branching and inheritance scenarios.

This test suite covers container branching including:
- Deep container inheritance chains
- Qualified instance inheritance
- Instance override behavior
- Cache inheritance across branches
"""

import pytest

from bevy import Container, Inject, injectable, Registry
from bevy.bundled.type_factory_hook import type_factory
from bevy.injection_types import Options


# Test services for container branching scenarios
class DatabaseConnection:
    def __init__(self, url: str = "sqlite://test.db"):
        self.url = url


class EmailService:
    def __init__(self, config: dict = None):
        self.config = config or {"smtp_host": "localhost"}


class CacheService:
    def __init__(self, ttl: int = 300):
        self.ttl = ttl


class UserRepository:
    def __init__(self, db: DatabaseConnection):
        self.db = db
    
    def find_user(self, user_id: str):
        return f"User {user_id} from {self.db.url}"


class TestBasicContainerBranching:
    """Test basic container branching functionality."""
    
    def test_child_inherits_parent_instances(self):
        """Test that child containers inherit parent instances."""
        registry = Registry()
        
        parent = Container(registry)
        parent.add(DatabaseConnection("parent-db"))
        
        child = parent.branch()
        
        # Child should inherit parent's instance
        parent_db = parent.get(DatabaseConnection)
        child_db = child.get(DatabaseConnection)
        
        assert parent_db.url == "parent-db"
        assert child_db.url == "parent-db"
        assert parent_db is child_db  # Should be the same instance
    
    def test_child_overrides_parent_instances(self):
        """Test that child containers can override parent instances."""
        registry = Registry()
        type_factory.register_hook(registry)
        
        parent = Container(registry)
        parent.add(DatabaseConnection("parent-db"))
        
        child = parent.branch()
        child.add(DatabaseConnection("child-db"))  # Override parent
        
        @injectable
        def use_db(db: Inject[DatabaseConnection]):
            return db.url
        
        parent_result = parent.call(use_db)
        child_result = child.call(use_db)
        
        assert parent_result == "parent-db"
        assert child_result == "child-db"  # Child overrides parent
    
    def test_parent_unaffected_by_child_changes(self):
        """Test that parent containers are unaffected by child modifications."""
        registry = Registry()
        
        parent = Container(registry)
        parent.add(DatabaseConnection("parent-db"))
        
        child = parent.branch()
        child.add(EmailService({"smtp_host": "child.smtp"}))  # Add new service to child
        
        # Parent should not see child's additions
        with pytest.raises(Exception):  # Should fail to resolve EmailService
            parent.get(EmailService)
        
        # Child should see both parent and its own services
        parent_db = child.get(DatabaseConnection)
        child_email = child.get(EmailService)
        
        assert parent_db.url == "parent-db"
        assert child_email.config["smtp_host"] == "child.smtp"


class TestDeepContainerInheritance:
    """Test complex container inheritance scenarios."""
    
    def test_deep_container_inheritance_chain(self):
        """Test behavior with multiple levels of container inheritance."""
        registry = Registry()
        
        # Create inheritance chain: grandparent -> parent -> child
        grandparent = Container(registry)
        grandparent.add(DatabaseConnection("grandparent-db"))
        
        parent = grandparent.branch()
        parent.add(EmailService({"smtp_host": "parent.smtp"}))
        
        child = parent.branch()
        child.add(CacheService(ttl=600))
        
        # Test direct access
        db = child.get(DatabaseConnection)
        email = child.get(EmailService)
        cache = child.get(CacheService)
        
        assert db.url == "grandparent-db"
        assert email.config["smtp_host"] == "parent.smtp"
        assert cache.ttl == 600
    
    def test_inheritance_chain_with_overrides(self):
        """Test inheritance chain where each level overrides services."""
        registry = Registry()
        
        # Each level adds its own version of DatabaseConnection
        grandparent = Container(registry)
        grandparent.add(DatabaseConnection("grandparent-db"))
        
        parent = grandparent.branch()
        parent.add(DatabaseConnection("parent-db"))  # Override grandparent
        
        child = parent.branch()
        child.add(DatabaseConnection("child-db"))  # Override parent
        
        # Each should use its own version
        grandparent_db = grandparent.get(DatabaseConnection)
        parent_db = parent.get(DatabaseConnection)
        child_db = child.get(DatabaseConnection)
        
        assert grandparent_db.url == "grandparent-db"
        assert parent_db.url == "parent-db"
        assert child_db.url == "child-db"
    
    def test_sibling_container_isolation(self):
        """Test that sibling containers are isolated from each other."""
        registry = Registry()
        
        parent = Container(registry)
        parent.add(DatabaseConnection("parent-db"))
        
        child1 = parent.branch()
        child1.add(EmailService({"smtp_host": "child1.smtp"}))
        
        child2 = parent.branch()
        child2.add(CacheService(ttl=1200))
        
        # Child1 should not see Child2's services and vice versa
        assert child1.get(DatabaseConnection).url == "parent-db"  # Inherited
        assert child1.get(EmailService).config["smtp_host"] == "child1.smtp"  # Own service
        
        with pytest.raises(Exception):  # Should not see child2's cache
            child1.get(CacheService)
        
        assert child2.get(DatabaseConnection).url == "parent-db"  # Inherited
        assert child2.get(CacheService).ttl == 1200  # Own service
        
        with pytest.raises(Exception):  # Should not see child1's email
            child2.get(EmailService)


class TestQualifiedInstanceInheritance:
    """Test inheritance of qualified instances."""
    
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
    
    def test_qualified_vs_unqualified_inheritance(self):
        """Test inheritance of qualified vs unqualified instances."""
        registry = Registry()
        parent = Container(registry)
        
        # Add both qualified and unqualified instances
        parent.add(DatabaseConnection("unqualified-db"))
        parent.add(DatabaseConnection, DatabaseConnection("qualified-db"), qualifier="special")
        
        child = parent.branch()
        
        # Test direct access
        regular_db = child.get(DatabaseConnection)
        # Access qualified instance through parent (child inherits it)
        special_db = parent.instances[(DatabaseConnection, "special")]
        
        assert regular_db.url == "unqualified-db"
        assert special_db.url == "qualified-db"
    
    def test_qualified_instance_override_isolation(self):
        """Test that qualified instance overrides don't affect other qualifiers."""
        registry = Registry()
        parent = Container(registry)
        
        # Add multiple qualified instances
        parent.add(DatabaseConnection, DatabaseConnection("parent-primary"), qualifier="primary")
        parent.add(DatabaseConnection, DatabaseConnection("parent-secondary"), qualifier="secondary")
        parent.add(DatabaseConnection, DatabaseConnection("parent-backup"), qualifier="backup")
        
        child = parent.branch()
        # Override only secondary
        child.add(DatabaseConnection, DatabaseConnection("child-secondary"), qualifier="secondary")
        
        @injectable
        def use_all_qualified(
            primary: Inject[DatabaseConnection, Options(qualifier="primary")],
            secondary: Inject[DatabaseConnection, Options(qualifier="secondary")],
            backup: Inject[DatabaseConnection, Options(qualifier="backup")]
        ):
            return f"Primary: {primary.url}, Secondary: {secondary.url}, Backup: {backup.url}"
        
        result = child.call(use_all_qualified)
        assert "parent-primary" in result    # Inherited
        assert "child-secondary" in result   # Overridden
        assert "parent-backup" in result     # Inherited


class TestFactoryCacheInheritance:
    """Test factory cache inheritance across container branches."""
    
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
    
    def test_factory_cache_override_in_child(self):
        """Test that child containers can override factory caches."""
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
        
        # Child manually adds a different instance with the factory as key
        child = parent.branch()
        child.instances[counting_factory] = DatabaseConnection("child-override")
        
        child_result = child.call(get_db)
        assert call_count == 1  # No additional factory call
        assert child_result == "child-override"  # Child's override
        
        # Parent should still have original
        parent_result2 = parent.call(get_db)
        assert parent_result2 == "factory-1"
    
    def test_factory_cache_isolation_between_siblings(self):
        """Test factory cache isolation between sibling containers."""
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
        
        # Create two child containers
        child1 = parent.branch()
        child2 = parent.branch()
        
        # Each child should create its own factory instance
        result1 = child1.call(get_db)
        result2 = child2.call(get_db)
        
        assert call_count == 2  # Each child calls factory
        assert result1 == "factory-1"
        assert result2 == "factory-2"
        
        # Subsequent calls within same child should reuse instance
        result1_again = child1.call(get_db)
        result2_again = child2.call(get_db)
        
        assert call_count == 2  # No additional calls
        assert result1_again == "factory-1"
        assert result2_again == "factory-2"

    def test_branch_injects_into_function_from_parent(self):
        def test(db: Inject[DatabaseConnection]):
            return db.url

        registry = Registry()
        parent = Container(registry)
        parent.add(DatabaseConnection("parent-db"))

        child = parent.branch()
        assert "parent-db" in child.call(test)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])