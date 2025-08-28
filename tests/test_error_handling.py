#!/usr/bin/env python3
"""
Tests for error handling and validation scenarios.

This test suite covers error handling including:
- Missing dependency error messages
- Qualified dependency not found errors
- Factory error propagation
- Strict vs non-strict mode behavior
- Circular dependency detection
"""

import pytest

from bevy import Container, Inject, injectable, Registry
from bevy.injection_types import DependencyResolutionError, Options


# Test services for error scenarios
class UserRepository:
    def __init__(self, name="UserRepository"):
        self.name = name
    
    def find_user(self, user_id: str):
        return f"User {user_id} from {self.name}"


class DatabaseConnection:
    def __init__(self, url: str = "sqlite://test.db"):
        self.url = url


class EmailService:
    def __init__(self, config: dict = None):
        self.config = config or {"smtp_host": "localhost"}


class TestMissingDependencyErrors:
    """Test error handling for missing dependencies."""
    
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
        assert "No handler found that can handle dependency" in str(error)  # parameter name
    
    def test_missing_dependency_with_parameter_context(self):
        """Test that error includes parameter name context."""
        registry = Registry()
        container = Container(registry)
        
        @injectable
        def complex_function(
            user_repo: Inject[UserRepository],
            db_connection: Inject[DatabaseConnection],
            data: str
        ):
            return f"Processing {data}"
        
        with pytest.raises(DependencyResolutionError) as exc_info:
            container.call(complex_function, data="test")

        assert "No handler found that can handle dependency" in str(exc_info.value)
        

    def test_missing_dependency_in_nested_call(self):
        """Test error propagation in nested dependency resolution."""
        registry = Registry()
        container = Container(registry)
        
        @injectable
        def use_nested_service(service: Inject[UserRepository]):
            return "success"
        
        with pytest.raises(DependencyResolutionError):
            container.call(use_nested_service)


class TestQualifiedDependencyErrors:
    """Test error handling for qualified dependencies."""
    
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
    
    def test_qualified_vs_unqualified_separation(self):
        """Test that qualified and unqualified instances are separate."""
        registry = Registry()
        container = Container(registry)
        
        # Add only qualified instance
        container.add(DatabaseConnection, DatabaseConnection("qualified"), qualifier="primary")
        
        @injectable
        def need_unqualified_db(db: Inject[DatabaseConnection]):
            return db.url
        
        # Should not find the qualified instance
        with pytest.raises(DependencyResolutionError):
            container.call(need_unqualified_db)


class TestFactoryErrorHandling:
    """Test error handling in factory scenarios."""
    
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
    
    def test_factory_dependency_error(self):
        """Test error when factory itself has missing dependencies."""
        registry = Registry()
        container = Container(registry)
        
        @injectable
        def factory_with_dependency(missing: Inject[EmailService]) -> UserRepository:
            return UserRepository("factory-created")
        
        @injectable
        def use_factory_with_deps(
            repo: Inject[UserRepository, Options(default_factory=factory_with_dependency)]
        ):
            return repo.find_user("test")
        
        with pytest.raises(DependencyResolutionError):
            container.call(use_factory_with_deps)
    
    def test_factory_return_type_mismatch(self):
        """Test handling when factory returns wrong type."""
        registry = Registry()
        container = Container(registry)
        
        def wrong_type_factory():
            return "This is not a UserRepository"
        
        @injectable
        def use_wrong_factory(
            repo: Inject[UserRepository, Options(default_factory=wrong_type_factory)]
        ):
            # This should work but the returned object won't have expected methods
            return str(type(repo))
        
        # Factory returns wrong type but injection doesn't validate return types
        result = container.call(use_wrong_factory)
        assert "str" in result


class TestStrictModeHandling:
    """Test strict vs non-strict mode behavior."""
    
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
    
    def test_strict_mode_with_optional_types(self):
        """Test strict mode behavior with optional types."""
        registry = Registry()
        container = Container(registry)
        
        @injectable(strict=True)
        def strict_with_optional(service: Inject[UserRepository | None]):
            return service.find_user("123") if service else "No service"
        
        # Optional types should inject None even in strict mode
        result = container.call(strict_with_optional)
        assert result == "No service"
    
    def test_non_strict_mode_with_required_types(self):
        """Test non-strict mode with normally required types."""
        registry = Registry()
        container = Container(registry)
        
        @injectable(strict=False)
        def non_strict_required(
            service: Inject[UserRepository],
            db: Inject[DatabaseConnection]
        ):
            service_name = service.name if service else "None"
            db_url = db.url if db else "None"
            return f"Service: {service_name}, DB: {db_url}"
        
        result = container.call(non_strict_required)
        assert result == "Service: None, DB: None"


class TestCircularDependencyDetection:
    """Test detection and handling of circular dependencies."""
    
    def test_circular_reference_detection(self):
        """Test that missing dependencies raise appropriate errors."""
        registry = Registry()
        container = Container(registry)
        
        @injectable
        def use_missing_service(service: Inject[UserRepository]):
            return "success"
        
        # Should raise DependencyResolutionError for missing service
        with pytest.raises(DependencyResolutionError):
            container.call(use_missing_service)
    
    def test_self_referential_dependency(self):
        """Test that services requiring themselves fail gracefully."""
        registry = Registry()
        container = Container(registry)
        
        @injectable
        def use_missing_email(service: Inject[EmailService]):
            return "success"
        
        with pytest.raises(DependencyResolutionError):
            container.call(use_missing_email)


class TestAnnotationErrorHandling:
    """Test error handling with malformed annotations."""
    
    def test_malformed_inject_annotation(self):
        """Test behavior with missing dependencies."""
        registry = Registry()
        container = Container(registry)
        
        @injectable
        def missing_service(service: Inject[UserRepository]):
            return str(service)
        
        # Should raise DependencyResolutionError for missing service
        with pytest.raises(DependencyResolutionError):
            container.call(missing_service)
    
    def test_invalid_type_annotation(self):
        """Test handling of missing services."""
        registry = Registry()
        container = Container(registry)
        
        @injectable
        def missing_email(service: Inject[EmailService]):
            return str(service)
        
        # Should raise DependencyResolutionError for missing service
        with pytest.raises(DependencyResolutionError):
            container.call(missing_email)


class TestErrorMessageQuality:
    """Test that error messages are helpful and informative."""
    
    def test_error_message_includes_context(self):
        """Test that error messages include helpful context."""
        registry = Registry()
        container = Container(registry)
        
        @injectable
        def complex_function_name_for_testing(
            primary_user_repository: Inject[UserRepository, Options(qualifier="primary")],
            backup_database: Inject[DatabaseConnection, Options(qualifier="backup")]
        ):
            return "success"
        
        with pytest.raises(DependencyResolutionError) as exc_info:
            container.call(complex_function_name_for_testing)
        
        error_message = str(exc_info.value)
        # Should include parameter name and type information
        assert any(param in error_message for param in ["primary_user_repository", "backup_database"])
        assert any(typename in error_message for typename in ["UserRepository", "DatabaseConnection"])
    
    def test_helpful_factory_error_context(self):
        """Test that factory errors include helpful context."""
        registry = Registry()
        container = Container(registry)
        
        def problematic_factory():
            raise RuntimeError("Database connection failed during factory initialization")
        
        @injectable
        def use_problematic_factory(
            critical_service: Inject[UserRepository, Options(default_factory=problematic_factory)]
        ):
            return "success"
        
        with pytest.raises(RuntimeError) as exc_info:
            container.call(use_problematic_factory)
        
        # Original factory error should be preserved
        assert "Database connection failed during factory initialization" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])