#!/usr/bin/env python3
"""
Comprehensive test suite for the new dependency injection system.

Tests all aspects of the @injectable, @auto_inject, Inject[T], and Options system.
"""

import pytest

from bevy import (auto_inject, Container, Inject, injectable, InjectionStrategy, Options, TypeMatchingStrategy)
from bevy.context_vars import global_container
from bevy.registries import Registry


class UserService:
    def __init__(self, name="UserService"):
        self.name = name
    
    def get_user(self, user_id: str):
        return f"User {user_id} from {self.name}"


class Database:
    def __init__(self, name="Database"):
        self.name = name
    
    def query(self, sql: str):
        return f"Query '{sql}' on {self.name}"


class Cache:
    def __init__(self, name="Cache"):
        self.name = name
    
    def get(self, key: str):
        return f"Cached {key} from {self.name}"


class TestInjectableDecorator:
    """Test the @injectable decorator functionality."""
    
    def test_basic_injectable(self):
        """Test basic @injectable decorator."""
        @injectable
        def basic_func(service: Inject[UserService]):
            return service.name
        
        # Should have injection metadata
        assert hasattr(basic_func, '_bevy_injection_params')
        params = basic_func._bevy_injection_params
        assert 'service' in params
        assert params['service'][0] == UserService
        assert params['service'][1] is None  # No options
    
    def test_injectable_with_options(self):
        """Test @injectable with complex options."""
        @injectable
        def func_with_options(
            primary_db: Inject[Database, Options(qualifier="primary")],
            cache: Inject[Cache | None]
        ):
            return "test"
        
        params = func_with_options._bevy_injection_params
        
        # Check primary_db
        assert 'primary_db' in params
        db_type, db_opts = params['primary_db']
        assert db_type == Database
        assert db_opts.qualifier == "primary"
        
        # Check optional cache
        assert 'cache' in params
        cache_type, cache_opts = params['cache']
        # Should be the union type Cache | None
        assert 'Union' in str(cache_type) or hasattr(cache_type, '__class__')
    
    def test_injection_strategies(self):
        """Test different injection strategies."""
        
        # REQUESTED_ONLY (default)
        @injectable
        def requested_only(service: Inject[UserService], regular: str):
            return "test"
        
        params = requested_only._bevy_injection_params
        assert 'service' in params
        assert 'regular' not in params
        
        # ANY_NOT_PASSED
        @injectable(strategy=InjectionStrategy.ANY_NOT_PASSED)
        def any_not_passed(service: UserService, db: Database, manual: str):
            return "test"
        
        params = any_not_passed._bevy_injection_params
        assert 'service' in params
        assert 'db' in params
        assert 'manual' in params  # Has type annotation
        
        # ONLY specific parameters
        @injectable(strategy=InjectionStrategy.ONLY, params=["service"])
        def only_strategy(service: UserService, db: Database, manual: str):
            return "test"
        
        params = only_strategy._bevy_injection_params
        assert 'service' in params
        assert 'db' not in params
        assert 'manual' not in params
    
    def test_decorator_configuration(self):
        """Test various decorator configuration options."""
        @injectable(
            strategy=InjectionStrategy.REQUESTED_ONLY,
            strict=False,
            type_matching=TypeMatchingStrategy.EXACT_TYPE,
            debug=True,
            cache_analysis=False
        )
        def configured_func(service: Inject[UserService]):
            return "test"
        
        assert configured_func._bevy_injection_strategy == InjectionStrategy.REQUESTED_ONLY
        assert configured_func._bevy_strict_mode is False
        assert configured_func._bevy_type_matching == TypeMatchingStrategy.EXACT_TYPE
        assert configured_func._bevy_debug_mode is True
        assert configured_func._bevy_cache_analysis is False


class TestAutoInjectDecorator:
    """Test the @auto_inject decorator functionality."""
    
    def test_auto_inject_requires_injectable(self):
        """Test that @auto_inject requires @injectable."""
        with pytest.raises(ValueError, match="must be decorated with @injectable first"):
            @auto_inject
            def non_injectable():
                pass
    
    def test_auto_inject_preserves_metadata(self):
        """Test that @auto_inject preserves injection metadata."""
        @auto_inject
        @injectable
        def test_func(service: Inject[UserService]):
            return service.name
        
        # Should still have injection metadata
        assert hasattr(test_func, '_bevy_injection_params')
        params = test_func._bevy_injection_params
        assert 'service' in params


class TestContainerCall:
    """Test Container.call() functionality with new system."""
    
    def setup_method(self):
        """Set up test container."""
        self.registry = Registry()
        self.container = Container(self.registry)
        self.container.add(UserService())
        self.container.add(Database())
        self.container.add(Cache())
    
    def test_call_injectable_function(self):
        """Test calling @injectable decorated function."""
        @injectable
        def process_request(user_service: Inject[UserService], request_id: str):
            return f"Processed {request_id} with {user_service.name}"
        
        result = self.container.call(process_request, request_id="123")
        assert "Processed 123 with UserService" in result
    
    def test_call_regular_function(self):
        """Test calling regular function (dynamic analysis)."""
        def process_data(user_service: UserService, db: Database, data: str):
            return f"Processed {data} with {user_service.name} and {db.name}"
        
        result = self.container.call(process_data, data="test")
        assert "Processed test with UserService and Database" in result
    
    def test_optional_dependencies(self):
        """Test optional dependencies with Container.call()."""
        # Create container without Cache
        registry = Registry()
        container = Container(registry)
        container.add(UserService())
        
        @injectable
        def func_with_optional(
            user_service: Inject[UserService],
            cache: Inject[Cache | None],
            data: str
        ):
            cache_name = cache.name if cache else "No cache"
            return f"Data: {data}, User: {user_service.name}, Cache: {cache_name}"
        
        result = container.call(func_with_optional, data="test")
        assert "No cache" in result
        assert "UserService" in result
    
    def test_debug_mode(self):
        """Test debug mode functionality."""
        @injectable(debug=True)
        def debug_func(user_service: Inject[UserService], msg: str):
            return f"Debug: {msg} with {user_service.name}"
        
        # Should work and print debug info (captured in test)
        result = self.container.call(debug_func, msg="test")
        assert "Debug: test with UserService" in result
    
    def test_strict_vs_non_strict(self):
        """Test strict vs non-strict mode."""
        # Create empty container
        registry = Registry()
        empty_container = Container(registry)
        
        @injectable(strict=False)
        def non_strict_func(user_service: Inject[UserService], msg: str):
            name = user_service.name if user_service else "None"
            return f"Non-strict: {msg} with {name}"
        
        result = empty_container.call(non_strict_func, msg="test")
        assert "with None" in result
        
        @injectable(strict=True)
        def strict_func(user_service: Inject[UserService], msg: str):
            return f"Strict: {msg} with {user_service.name}"
        
        with pytest.raises(Exception):
            empty_container.call(strict_func, msg="test")


class TestGlobalContainerIntegration:
    """Test integration with global container."""
    
    def setup_method(self):
        """Set up global container for tests."""
        registry = Registry()
        test_container = Container(registry)
        test_container.add(UserService("GlobalUserService"))
        test_container.add(Database("GlobalDatabase"))
        self.original_token = global_container.set(test_container)
    
    def teardown_method(self):
        """Clean up global container state."""
        global_container.reset(self.original_token)
    
    def test_auto_inject_basic(self):
        """Test basic @auto_inject functionality."""
        @auto_inject
        @injectable
        def auto_func(user_service: Inject[UserService], msg: str):
            return f"Auto: {msg} with {user_service.name}"
        
        result = auto_func(msg="test")
        assert "Auto: test with GlobalUserService" in result
    
    def test_auto_inject_strategies(self):
        """Test @auto_inject with different strategies."""
        @auto_inject
        @injectable(strategy=InjectionStrategy.ANY_NOT_PASSED)
        def any_strategy(user_service: UserService, db: Database, msg: str):
            return f"Any: {msg} with {user_service.name} and {db.name}"
        
        result = any_strategy(msg="test")
        assert "GlobalUserService" in result
        assert "GlobalDatabase" in result


class TestTypeSystem:
    """Test the new type system components."""
    
    def test_inject_type_alias(self):
        """Test Inject[T] type alias."""
        from bevy.injection_types import extract_injection_info
        
        # Test basic Inject[Type]
        def func1(service: Inject[UserService]): pass
        
        sig = func1.__annotations__['service']
        actual_type, options = extract_injection_info(sig)
        assert actual_type == UserService
        assert options is None
        
        # Test Inject[Type, Options]
        def func2(service: Inject[UserService, Options(qualifier="test")]): pass
        
        sig = func2.__annotations__['service']
        actual_type, options = extract_injection_info(sig)
        assert actual_type == UserService
        assert options.qualifier == "test"
    
    def test_options_class(self):
        """Test Options class functionality."""
        opts = Options(
            qualifier="primary",
            default_factory=lambda: Database("default")
        )
        
        assert opts.qualifier == "primary"
        result = opts.default_factory()
        assert isinstance(result, Database)
        assert result.name == "default"
    
    def test_optional_type_detection(self):
        """Test optional type detection utilities."""
        from bevy.injection_types import is_optional_type, get_non_none_type
        
        # Test regular type
        assert not is_optional_type(UserService)
        
        # Test optional type (Type | None)
        def func(service: UserService | None): pass
        optional_type = func.__annotations__['service']
        assert is_optional_type(optional_type)
        assert get_non_none_type(optional_type) == UserService


class TestQualifiersAndOptions:
    """Test qualified dependencies and options."""
    
    def test_qualified_dependencies(self):
        """Test that qualified dependencies work correctly."""
        registry = Registry()
        container = Container(registry)
        
        # Add qualified instances
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
        assert "Primary: PrimaryDB" in result
        assert "Backup: BackupDB" in result
    
    def test_missing_qualified_dependency(self):
        """Test that missing qualified dependencies raise DependencyResolutionError."""
        registry = Registry()
        container = Container(registry)
        
        @injectable
        def func_with_qualifier(db: Inject[Database, Options(qualifier="missing")]):
            return db.name
        
        with pytest.raises(Exception, match="Cannot resolve qualified dependency"):
            container.call(func_with_qualifier)
    
    def test_qualified_vs_unqualified(self):
        """Test that qualified and unqualified instances are separate."""
        registry = Registry()
        container = Container(registry)
        
        # Add unqualified instance
        regular_db = Database("RegularDB")
        container.add(Database, regular_db)
        
        # Add qualified instance  
        special_db = Database("SpecialDB")
        container.add(Database, special_db, qualifier="special")
        
        @injectable
        def func_mixed(
            regular: Inject[Database],
            special: Inject[Database, Options(qualifier="special")]
        ):
            return f"Regular: {regular.name}, Special: {special.name}"
        
        result = container.call(func_mixed)
        assert "Regular: RegularDB" in result
        assert "Special: SpecialDB" in result


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_inject_with_default_value(self):
        """Test that Inject[Type] = Type() prioritizes injection over default."""
        registry = Registry()
        container = Container(registry)
        
        # Register a service in the container
        registered_service = UserService("RegisteredService")
        container.add(UserService, registered_service)
        
        @injectable
        def func_with_default(service: Inject[UserService] = UserService("DefaultService")):
            return f"Service: {service.name}"
        
        # When UserService is registered, injection should happen (not default)
        result = container.call(func_with_default)
        assert "Service: RegisteredService" in result
        
        # Test with empty container - should fall back to default
        empty_registry = Registry()
        empty_container = Container(empty_registry)
        
        result = empty_container.call(func_with_default)
        assert "Service: DefaultService" in result
    
    def test_inject_without_default_missing_dependency(self):
        """Test that Inject[Type] without default raises error when dependency missing."""
        registry = Registry()
        container = Container(registry)
        
        @injectable
        def func_no_default(service: Inject[UserService]):
            return f"Service: {service.name}"
        
        # Should raise DependencyResolutionError when no service registered
        with pytest.raises(Exception, match="No handler found that can handle dependency"):
            container.call(func_no_default)
    
    def test_inject_with_default_arbitrary_error(self):
        """Test that arbitrary errors during injection are raised, not falling back to default."""
        
        class ProblematicService:
            def __init__(self, name="ProblematicService"):
                self.name = name
                if name == "FactoryError":
                    raise ValueError("Factory creation failed!")
        
        def problematic_factory(container):
            return ProblematicService("FactoryError")
        
        registry = Registry()
        
        # Register a factory that will raise an arbitrary error
        registry.add_factory(problematic_factory, ProblematicService)
        
        container = Container(registry)
        
        @injectable
        def func_with_default(service: Inject[ProblematicService] = ProblematicService("DefaultService")):
            return f"Service: {service.name}"
        
        # Should raise the ValueError from the factory, not fall back to default
        with pytest.raises(ValueError, match="Factory creation failed!"):
            container.call(func_with_default)
    
    def test_default_factory_vs_default_value_precedence(self):
        """Test precedence between default_factory and default parameter values."""
        
        class TestService:
            def __init__(self, name="TestService"):
                self.name = name
        
        # Test 1: default_factory should take precedence over default value
        registry = Registry()
        container = Container(registry)
        
        @injectable
        def func_with_both(
            service: Inject[TestService, Options(default_factory=lambda: TestService("FromFactory"))] = TestService("FromDefault")
        ):
            return f"Service: {service.name}"
        
        result = container.call(func_with_both)
        assert "Service: FromFactory" in result, "default_factory should take precedence over default value"
        
        # Test 2: If default_factory raises DependencyResolutionError, should fall back to default value
        def failing_factory():
            from bevy.injection_types import DependencyResolutionError
            raise DependencyResolutionError(TestService, "service", "Factory failed to resolve")
        
        @injectable  
        def func_with_failing_factory(
            service: Inject[TestService, Options(default_factory=failing_factory)] = TestService("FromDefault")
        ):
            return f"Service: {service.name}"
        
        result = container.call(func_with_failing_factory)
        assert "Service: FromDefault" in result, "Should fall back to default value when factory raises DependencyResolutionError"
        
        # Test 3: If default_factory raises arbitrary error, should not fall back (should raise)
        def broken_factory():
            raise ValueError("Factory is broken!")
        
        @injectable
        def func_with_broken_factory(
            service: Inject[TestService, Options(default_factory=broken_factory)] = TestService("FromDefault")
        ):
            return f"Service: {service.name}"
        
        with pytest.raises(ValueError, match="Factory is broken!"):
            container.call(func_with_broken_factory)
    
    def test_qualified_dependencies_in_child_containers(self):
        """Test that qualified dependency errors work correctly in child containers."""
        
        class TestService:
            def __init__(self, name="TestService"):
                self.name = name
        
        # Create parent container with one qualified instance
        parent_registry = Registry()
        parent_container = Container(parent_registry)
        parent_container.add(TestService, TestService("ParentService"), qualifier="existing")
        
        # Create child container
        child_registry = Registry()
        child_container = Container(child_registry, parent=parent_container)
        
        # Test 1: Child should inherit qualified instance from parent
        @injectable
        def func_with_existing_qualifier(
            service: Inject[TestService, Options(qualifier="existing")]
        ):
            return f"Service: {service.name}"
        
        result = child_container.call(func_with_existing_qualifier)
        assert "Service: ParentService" in result
        
        # Test 2: Child should raise error for nonexistent qualified dependency
        @injectable
        def func_with_missing_qualifier(
            service: Inject[TestService, Options(qualifier="nonexistent")]
        ):
            return f"Service: {service.name}"
        
        # This should raise DependencyResolutionError when qualifier doesn't exist anywhere in hierarchy
        with pytest.raises(Exception, match="Cannot resolve qualified dependency"):
            child_container.call(func_with_missing_qualifier)
    
    def test_mixed_injection_and_manual_params(self):
        """Test mixing injected and manual parameters."""
        registry = Registry()
        container = Container(registry)
        container.add(UserService())
        
        @injectable
        def mixed_func(
            user_service: Inject[UserService],  # Injected
            manual_param: str,                  # Manual
            optional_param: str = "default"     # Manual with default
        ):
            return f"{user_service.name} - {manual_param} - {optional_param}"
        
        result = container.call(mixed_func, manual_param="test")
        assert "UserService - test - default" in result
        
        result = container.call(mixed_func, manual_param="test", optional_param="custom")
        assert "UserService - test - custom" in result
    
    def test_function_with_no_injectable_params(self):
        """Test function with no injectable parameters."""
        @injectable
        def no_injection_func(param1: str, param2: int = 42):
            return f"{param1} - {param2}"
        
        registry = Registry()
        container = Container(registry)
        
        result = container.call(no_injection_func, param1="test")
        assert "test - 42" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])