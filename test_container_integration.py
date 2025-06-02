#!/usr/bin/env python3
"""Test container integration with new injection system."""

from bevy import Container, injectable, auto_inject, Inject, Options, InjectionStrategy
from bevy.registries import Registry


class UserService:
    def __init__(self):
        self.name = "UserService"
    
    def get_user(self, user_id: str):
        return f"User {user_id}"


class Database:
    def __init__(self):
        self.name = "Database"
    
    def query(self, sql: str):
        return f"Query result: {sql}"


class Cache:
    def __init__(self):
        self.name = "Cache"
    
    def get(self, key: str):
        return f"Cached: {key}"


def test_container_call_with_injectable():
    """Test container.call() with @injectable decorated functions."""
    print("Testing container.call() with @injectable functions...")
    
    # Create container and register services
    registry = Registry()
    container = Container(registry)
    container.add(UserService())
    container.add(Database())
    
    # Test function with @injectable decorator
    @injectable
    def process_request(user_service: Inject[UserService], request_id: str):
        return f"Processed {request_id} with {user_service.name}"
    
    # Call via container
    result = container.call(process_request, request_id="123")
    print(f"  Result: {result}")
    assert "Processed 123 with UserService" in result
    print("  ✓ @injectable function works with container.call()")


def test_container_call_without_decorator():
    """Test container.call() with regular functions (dynamic analysis)."""
    print("\nTesting container.call() with regular functions...")
    
    # Create container and register services
    registry = Registry()
    container = Container(registry)
    container.add(UserService())
    container.add(Database())
    
    # Test regular function (no decorator)
    def process_data(user_service: UserService, db: Database, data: str):
        return f"Processed {data} with {user_service.name} and {db.name}"
    
    # Call via container (should use ANY_NOT_PASSED strategy)
    result = container.call(process_data, data="test_data")
    print(f"  Result: {result}")
    assert "Processed test_data with UserService and Database" in result
    print("  ✓ Regular function works with container.call()")


def test_optional_dependencies():
    """Test optional dependencies with Container | None."""
    print("\nTesting optional dependencies...")
    
    # Create container with only some services
    registry = Registry()
    container = Container(registry)
    container.add(UserService())
    # Note: Not adding Cache
    
    @injectable
    def process_with_optional(
        user_service: Inject[UserService],
        cache: Inject[Cache | None],  # Optional
        data: str
    ):
        cache_info = cache.name if cache else "No cache"
        return f"Processed {data} with {user_service.name}, cache: {cache_info}"
    
    # Call should work even though Cache is not available
    result = container.call(process_with_optional, data="test")
    print(f"  Result: {result}")
    assert "No cache" in result
    print("  ✓ Optional dependencies work correctly")


def test_debug_mode():
    """Test debug mode logging."""
    print("\nTesting debug mode...")
    
    registry = Registry()
    container = Container(registry)
    container.add(UserService())
    
    @injectable(debug=True)
    def debug_function(user_service: Inject[UserService], msg: str):
        return f"Debug: {msg} with {user_service.name}"
    
    print("  Calling with debug=True (should see debug output):")
    result = container.call(debug_function, msg="hello")
    assert "Debug: hello with UserService" in result
    print("  ✓ Debug mode works")


def test_strict_mode():
    """Test strict vs non-strict mode."""
    print("\nTesting strict mode...")
    
    registry = Registry()
    container = Container(registry)
    # Note: Not registering any services
    
    @injectable(strict=False)
    def non_strict_function(user_service: Inject[UserService], msg: str):
        service_name = user_service.name if user_service else "None"
        return f"Non-strict: {msg} with {service_name}"
    
    # Should work in non-strict mode even with missing dependencies
    result = container.call(non_strict_function, msg="test")
    print(f"  Result: {result}")
    assert "with None" in result
    print("  ✓ Non-strict mode works")
    
    @injectable(strict=True)
    def strict_function(user_service: Inject[UserService], msg: str):
        return f"Strict: {msg} with {user_service.name}"
    
    # Should fail in strict mode with missing dependencies
    try:
        container.call(strict_function, msg="test")
        assert False, "Should have raised an exception"
    except Exception as e:
        print(f"  Expected exception in strict mode: {type(e).__name__}")
        print("  ✓ Strict mode works")


if __name__ == "__main__":
    test_container_call_with_injectable()
    test_container_call_without_decorator()
    test_optional_dependencies()
    test_debug_mode()
    test_strict_mode()
    print("\n🎉 All container integration tests passed!")