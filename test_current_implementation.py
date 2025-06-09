#!/usr/bin/env python3
"""Test script to verify current implementation works correctly."""

from bevy import Container, Registry, injectable, Inject
from bevy.injection_types import Options


class Database:
    def __init__(self, name: str):
        self.name = name
    
    def __repr__(self):
        return f"Database({self.name})"


def test_qualified_dependency():
    """Test from the test suite that should pass."""
    registry = Registry()
    container = Container(registry)
    
    primary_db = Database("PrimaryDB")
    backup_db = Database("BackupDB")
    
    container.add(Database, primary_db, qualifier="primary")
    container.add(Database, backup_db, qualifier="backup")
    
    @injectable
    def func_with_qualifiers(
        primary: Inject[Database, Options(qualifier="primary")],
        backup: Inject[Database, Options(qualifier="backup")]
    ):
        return f"Primary: {primary.name}, Backup: {backup.name}"
    
    result = container.call(func_with_qualifiers)
    print(f"SUCCESS: {result}")
    assert "Primary: PrimaryDB" in result
    assert "Backup: BackupDB" in result


def test_missing_qualified_dependency():
    """Test that should fail with proper error."""
    registry = Registry()
    container = Container(registry)
    
    @injectable
    def func_with_qualifier(db: Inject[Database, Options(qualifier="missing")]):
        return db.name
    
    try:
        container.call(func_with_qualifier)
        print("ERROR: Should have failed!")
    except Exception as e:
        print(f"SUCCESS: Correctly failed with: {e}")


def test_direct_container_get():
    """Test direct container.get with qualifiers."""
    registry = Registry()
    container = Container(registry)
    
    primary_db = Database("DirectPrimary")
    container.add(Database, primary_db, qualifier="primary")
    
    # This should work
    result = container.get(Database, qualifier="primary")
    print(f"Direct get SUCCESS: {result}")
    assert result.name == "DirectPrimary"
    
    # Test the equivalent with injection
    @injectable  
    def get_via_injection(db: Inject[Database, Options(qualifier="primary")]):
        return db
    
    injected_result = container.call(get_via_injection)
    print(f"Injection SUCCESS: {injected_result}")
    assert injected_result.name == "DirectPrimary"
    
    # Verify they're the same instance
    assert result is injected_result


if __name__ == "__main__":
    test_qualified_dependency()
    test_missing_qualified_dependency()
    test_direct_container_get()
    print("All tests passed!")