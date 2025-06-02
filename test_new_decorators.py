#!/usr/bin/env python3
"""Test script for new @injectable and @auto_inject decorators."""

from bevy.injection_types import Inject, Options, InjectionStrategy
from bevy.injections import injectable, auto_inject, get_injection_info, is_injectable


class UserService:
    def get_user(self, user_id: str):
        return f"User {user_id}"


class Database:
    def query(self, sql: str):
        return f"Query result: {sql}"


class Cache:
    def get(self, key: str):
        return f"Cached: {key}"


def test_injectable_decorator():
    """Test @injectable decorator functionality."""
    print("Testing @injectable decorator...")
    
    # Test basic injectable function without parentheses
    @injectable
    def basic_func(service: Inject[UserService]):
        return service.get_user("123")
    
    # Check metadata was stored
    print(f"  Is injectable: {is_injectable(basic_func)}")
    info = get_injection_info(basic_func)
    print(f"  Info: {info}")
    if info:
        print(f"  Params: {info['params']}")
    
    assert is_injectable(basic_func)
    assert info is not None
    assert 'service' in info['params']
    assert info['params']['service'][0] == UserService
    print("  ✓ Basic @injectable works")
    
    # Test with options using parentheses
    @injectable()
    def with_options(
        primary_db: Inject[Database, Options(qualifier="primary")],
        cache: Inject[Cache | None]
    ):
        return "processed"
    
    info = get_injection_info(with_options)
    assert 'primary_db' in info['params']
    assert 'cache' in info['params']
    primary_type, primary_opts = info['params']['primary_db']
    assert primary_type == Database
    assert primary_opts.qualifier == "primary"
    print("  ✓ @injectable with options works")
    
    # Test ANY_NOT_PASSED strategy
    @injectable(strategy=InjectionStrategy.ANY_NOT_PASSED)
    def auto_inject_func(service: UserService, db: Database, manual_param: str):
        return f"service: {service}, db: {db}, manual: {manual_param}"
    
    info = get_injection_info(auto_inject_func)
    assert 'service' in info['params']
    assert 'db' in info['params']
    assert 'manual_param' in info['params']  # Has type annotation so will be injected
    print("  ✓ ANY_NOT_PASSED strategy works")
    
    # Test ONLY strategy
    @injectable(strategy=InjectionStrategy.ONLY, params=["service"])
    def selective_func(service: UserService, db: Database, manual: str):
        return "selective"
    
    info = get_injection_info(selective_func)
    assert 'service' in info['params']
    assert 'db' not in info['params']
    assert 'manual' not in info['params']
    print("  ✓ ONLY strategy works")


def test_auto_inject_decorator():
    """Test @auto_inject decorator functionality."""
    print("\nTesting @auto_inject decorator...")
    
    # Test that auto_inject requires injectable
    try:
        @auto_inject
        def non_injectable_func():
            pass
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "must be decorated with @injectable first" in str(e)
        print("  ✓ @auto_inject validates @injectable requirement")
    
    # Test proper usage (injectable must be applied first)
    @injectable
    def injectable_func(service: Inject[UserService]):
        return service.get_user("456")
    
    # Now apply auto_inject
    proper_func = auto_inject(injectable_func)
    
    # Check that metadata is preserved
    assert is_injectable(proper_func)
    info = get_injection_info(proper_func)
    assert info is not None
    assert 'service' in info['params']
    print("  ✓ @auto_inject preserves metadata")


def test_function_analysis():
    """Test function signature analysis."""
    print("\nTesting function signature analysis...")
    
    @injectable
    def complex_func(
        required_service: Inject[UserService],
        optional_cache: Inject[Cache | None],
        qualified_db: Inject[Database, Options(qualifier="primary")],
        regular_param: str
    ):
        return "complex"
    
    info = get_injection_info(complex_func)
    params = info['params']
    
    # Check required service
    assert 'required_service' in params
    service_type, service_opts = params['required_service']
    assert service_type == UserService
    assert service_opts is None
    
    # Check optional cache
    assert 'optional_cache' in params
    cache_type, cache_opts = params['optional_cache']
    # Should extract Cache | None union type
    assert hasattr(cache_type, '__class__') and ('UnionType' in str(type(cache_type)) or 'Union' in str(cache_type))
    
    # Check qualified database
    assert 'qualified_db' in params
    db_type, db_opts = params['qualified_db']
    assert db_type == Database
    assert db_opts.qualifier == "primary"
    
    # Check regular param not included (no Inject[])
    assert 'regular_param' not in params
    
    print("  ✓ Function signature analysis works correctly")


if __name__ == "__main__":
    test_injectable_decorator()
    test_auto_inject_decorator()
    test_function_analysis()
    print("\n🎉 All decorator tests passed!")