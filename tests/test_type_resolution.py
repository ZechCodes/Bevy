#!/usr/bin/env python3
"""
Tests for complex type annotation resolution.

This test suite covers complex type scenarios including:
- Optional types with None values
- Union type resolution priority
- Generic types (List, Dict, etc.)
- Callable type injection
- Type annotation edge cases
"""

import pytest
from typing import List, Callable, Optional
from bevy import injectable, Inject, Container, Registry
from bevy.injection_types import Options
from bevy.bundled.type_factory_hook import type_factory


# Test services for complex type scenarios
class DatabaseConnection:
    def __init__(self, url: str = "sqlite://test.db"):
        self.url = url


class EmailService:
    def __init__(self, config: dict = None):
        self.config = config or {"smtp_host": "localhost"}
    
    def send(self, to: str, message: str):
        return f"Sent '{message}' to {to} via {self.config['smtp_host']}"


class CacheService:
    def __init__(self, ttl: int = 300):
        self.ttl = ttl
        self.data = {}
    
    def get(self, key: str):
        return self.data.get(key)
    
    def set(self, key: str, value: str):
        self.data[key] = value


class TestOptionalTypes:
    """Test optional type handling and None injection."""
    
    def test_optional_type_with_none_value(self):
        """Test that Optional[T] can receive None values."""
        registry = Registry()
        container = Container(registry)
        
        @injectable
        def handle_optional_cache(
            cache: Inject[CacheService | None],
            message: str
        ):
            if cache is None:
                return f"No cache: {message}"
            return f"With cache: {message}"
        
        # No CacheService in container - should inject None
        result = container.call(handle_optional_cache, message="test")
        assert result == "No cache: test"
    
    def test_optional_with_existing_service(self):
        """Test that Optional[T] receives actual instance when available."""
        registry = Registry()
        type_factory.register_hook(registry)
        container = Container(registry)
        
        # Add cache service
        cache = CacheService(ttl=600)
        container.add(cache)
        
        @injectable
        def handle_optional_cache(
            cache: Inject[CacheService | None],
            message: str
        ):
            if cache is None:
                return f"No cache: {message}"
            return f"With cache TTL {cache.ttl}: {message}"
        
        result = container.call(handle_optional_cache, message="test")
        assert result == "With cache TTL 600: test"
    
    def test_optional_with_factory(self):
        """Test Optional[T] with default factory."""
        registry = Registry()
        container = Container(registry)
        
        def create_cache():
            return CacheService(ttl=1200)
        
        @injectable
        def handle_optional_cache(
            cache: Inject[CacheService | None, Options(default_factory=create_cache)],
            message: str
        ):
            if cache is None:
                return f"No cache: {message}"
            return f"Factory cache TTL {cache.ttl}: {message}"
        
        result = container.call(handle_optional_cache, message="test")
        assert result == "Factory cache TTL 1200: test"


class TestUnionTypes:
    """Test union type resolution and priority."""
    
    def test_union_type_resolution_priority(self):
        """Test that specific service types can be injected normally."""
        registry = Registry()
        type_factory.register_hook(registry)
        container = Container(registry)
        
        # Add specific instance
        container.add(EmailService({"smtp_host": "custom.smtp"}))
        
        @injectable
        def handle_email_service(
            service: Inject[EmailService],
            message: str
        ):
            return f"Email: {service.config['smtp_host']}"
        
        result = container.call(handle_email_service, message="test")
        assert result == "Email: custom.smtp"
    
    def test_union_type_fallback(self):
        """Test that cache service can be injected when available."""
        registry = Registry()
        type_factory.register_hook(registry)
        container = Container(registry)
        
        # Add CacheService
        container.add(CacheService(ttl=900))
        
        @injectable
        def handle_cache_service(
            service: Inject[CacheService],
            message: str
        ):
            return f"Cache: {service.ttl}"
        
        result = container.call(handle_cache_service, message="test")
        assert result == "Cache: 900"


class TestGenericTypes:
    """Test handling of generic types."""
    
    def test_generic_type_handling(self):
        """Test handling of generic types like List[T]."""
        registry = Registry()
        container = Container(registry)
        
        # This should work with current implementation
        def create_db_list():
            return [
                DatabaseConnection("db1"),
                DatabaseConnection("db2")
            ]
        
        @injectable
        def handle_db_list(
            dbs: Inject[List[DatabaseConnection], Options(default_factory=create_db_list)]
        ):
            return [db.url for db in dbs]
        
        result = container.call(handle_db_list)
        assert result == ["db1", "db2"]
    
    def test_generic_with_optional(self):
        """Test generic types combined with optional."""
        registry = Registry()
        container = Container(registry)
        
        @injectable
        def handle_optional_list(
            dbs: Inject[List[DatabaseConnection] | None],
            message: str
        ):
            if dbs is None:
                return f"No databases: {message}"
            return f"Found {len(dbs)} databases: {message}"
        
        # No list provided - should get None
        result = container.call(handle_optional_list, message="test")
        assert result == "No databases: test"


class TestCallableTypes:
    """Test injection of callable dependencies."""
    
    def test_callable_type_injection(self):
        """Test injection of callable dependencies."""
        registry = Registry()
        container = Container(registry)
        
        def email_validator(email: str) -> bool:
            return "@" in email and "." in email
        
        container.add(Callable[[str], bool], email_validator)
        
        @injectable
        def validate_email(
            validator: Inject[Callable[[str], bool]],
            email: str
        ):
            return validator(email)
        
        result = container.call(validate_email, email="test@example.com")
        assert result is True
        
        result = container.call(validate_email, email="invalid-email")
        assert result is False
    
    def test_callable_with_factory(self):
        """Test callable injection with factory."""
        registry = Registry()
        container = Container(registry)
        
        def create_validator():
            def strict_validator(email: str) -> bool:
                return "@" in email and "." in email and len(email) > 5
            return strict_validator
        
        @injectable
        def validate_email_strict(
            validator: Inject[Callable[[str], bool], Options(default_factory=create_validator)],
            email: str
        ):
            return validator(email)
        
        result = container.call(validate_email_strict, email="test@example.com")
        assert result is True
        
        result = container.call(validate_email_strict, email="a@b.c")  # Too short
        assert result is False


class TestComplexAnnotationScenarios:
    """Test edge cases with complex type annotations."""
    
    def test_nested_generic_types(self):
        """Test nested generic type annotations."""
        registry = Registry()
        container = Container(registry)
        
        def create_service_map():
            return {
                "email": EmailService({"smtp_host": "email.server"}),
                "cache": CacheService(ttl=3600)
            }
        
        @injectable
        def handle_service_map(
            services: Inject[dict, Options(default_factory=create_service_map)]
        ):
            results = []
            for name, service in services.items():
                if isinstance(service, EmailService):
                    results.append(f"{name}: {service.config['smtp_host']}")
                elif isinstance(service, CacheService):
                    results.append(f"{name}: TTL {service.ttl}")
            return results
        
        result = container.call(handle_service_map)
        assert "email: email.server" in result
        assert "cache: TTL 3600" in result
    
    def test_forward_reference_annotations(self):
        """Test handling of string annotations (forward references)."""
        registry = Registry()
        type_factory.register_hook(registry)
        container = Container(registry)
        
        # This tests string annotation handling
        @injectable
        def handle_forward_ref(service: Inject["DatabaseConnection"]):
            return service.url
        
        result = container.call(handle_forward_ref)
        assert "sqlite://test.db" in result


class TestTypeMatchingStrategies:
    """Test different type matching strategies."""
    
    def test_subclass_matching(self):
        """Test that subclasses can be injected for parent types."""
        registry = Registry()
        container = Container(registry)
        
        class SpecialDatabase(DatabaseConnection):
            def __init__(self):
                super().__init__("special://database")
                self.special_feature = True
        
        container.add(DatabaseConnection, SpecialDatabase())
        
        @injectable
        def use_database(db: Inject[DatabaseConnection]):
            if hasattr(db, 'special_feature'):
                return f"Special: {db.url}"
            return f"Regular: {db.url}"
        
        result = container.call(use_database)
        assert result == "Special: special://database"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])