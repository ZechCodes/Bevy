#!/usr/bin/env python3
"""Test @auto_inject integration with global container."""

from bevy import injectable, auto_inject, Inject
from bevy import Container
from bevy.registries import Registry
from bevy.context_vars import global_container
from bevy.injection_types import InjectionStrategy


class UserService:
    def __init__(self):
        self.name = "GlobalUserService"
    
    def get_user(self, user_id: str):
        return f"User {user_id}"


class Database:
    def __init__(self):
        self.name = "GlobalDatabase"


def test_auto_inject_with_global_container():
    """Test @auto_inject using the global container."""
    print("Testing @auto_inject with global container...")
    
    # Set up global container
    registry = Registry()
    test_container = Container(registry)
    test_container.add(UserService())
    test_container.add(Database())
    
    # Set as global container using context variable
    global_container.set(test_container)
    
    # Function with auto injection (apply injectable first, then auto_inject)
    @auto_inject
    @injectable
    def process_request(user_service: Inject[UserService], request_id: str):
        return f"Auto-injected: {request_id} with {user_service.name}"
    
    # Call function directly - should auto-inject from global container
    result = process_request(request_id="456")
    print(f"  Result: {result}")
    assert "Auto-injected: 456 with GlobalUserService" in result
    print("  ✓ @auto_inject works with global container")


def test_auto_inject_with_optional():
    """Test @auto_inject with optional dependencies."""
    print("\nTesting @auto_inject with optional dependencies...")
    
    # Set up global container with limited services
    registry = Registry()
    test_container = Container(registry)
    test_container.add(UserService())
    # Not adding Database
    
    global_container.set(test_container)
    
    @auto_inject
    @injectable
    def process_with_optional(
        user_service: Inject[UserService], 
        db: Inject[Database | None],
        message: str
    ):
        db_name = db.name if db else "No database"
        return f"Optional test: {message}, user: {user_service.name}, db: {db_name}"
    
    result = process_with_optional(message="hello")
    print(f"  Result: {result}")
    assert "No database" in result and "GlobalUserService" in result
    print("  ✓ @auto_inject works with optional dependencies")


def test_auto_inject_different_strategies():
    """Test @auto_inject with different injection strategies."""
    print("\nTesting @auto_inject with different strategies...")
    
    registry = Registry()
    test_container = Container(registry)
    test_container.add(UserService())
    test_container.add(Database())
    global_container.set(test_container)
    
    # ANY_NOT_PASSED strategy
    @auto_inject
    @injectable(strategy=InjectionStrategy.ANY_NOT_PASSED)
    def any_not_passed_func(user_service: UserService, db: Database, msg: str):
        return f"Any strategy: {msg} with {user_service.name} and {db.name}"
    
    result = any_not_passed_func(msg="test")
    print(f"  ANY_NOT_PASSED result: {result}")
    assert "GlobalUserService" in result and "GlobalDatabase" in result
    print("  ✓ ANY_NOT_PASSED strategy works")
    
    # ONLY strategy
    @auto_inject
    @injectable(strategy=InjectionStrategy.ONLY, params=["user_service"])
    def only_strategy_func(user_service: UserService, db: Database, msg: str):
        # Only user_service should be injected, db must be passed manually
        return f"Only strategy: {msg} with {user_service.name}"
    
    # This should work because only user_service gets injected
    manual_db = Database()
    manual_db.name = "ManualDatabase"
    result = only_strategy_func(db=manual_db, msg="test")
    print(f"  ONLY strategy result: {result}")
    assert "GlobalUserService" in result
    print("  ✓ ONLY strategy works")


if __name__ == "__main__":
    # Import here to avoid issues with global container not being set
    from bevy.injection_types import InjectionStrategy
    
    test_auto_inject_with_global_container()
    test_auto_inject_with_optional()
    test_auto_inject_different_strategies()
    print("\n🎉 All @auto_inject integration tests passed!")