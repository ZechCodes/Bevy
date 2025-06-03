#!/usr/bin/env python3
"""
Tests for performance with larger dependency graphs.

This test suite covers performance scenarios including:
- Large dependency counts
- Nested dependency resolution chains
- Complex dependency graphs
- Performance regression detection
"""

import pytest
import time
from bevy import injectable, Inject, Container, Registry
from bevy.bundled.type_factory_hook import type_factory


class TestLargeDependencyGraphs:
    """Test performance with many dependencies."""
    
    def test_large_dependency_count(self):
        """Test performance with many dependencies."""
        registry = Registry()
        type_factory.register_hook(registry)
        container = Container(registry)
        
        # Create 50 different service types
        service_types = []
        for i in range(50):
            service_class = type(f"Service{i}", (), {
                "__init__": lambda self, value=i: setattr(self, "value", value)
            })
            service_types.append(service_class)
            container.add(service_class())
        
        # Create a function that depends on all of them
        annotations = {f"service_{i}": Inject[service_types[i]] for i in range(50)}
        
        @injectable
        def use_many_services(**services):
            return sum(service.value for service in services.values())
        
        # Manually set annotations (since we can't dynamically create parameter list)
        use_many_services.__annotations__ = annotations
        
        start_time = time.time()
        result = container.call(use_many_services)
        end_time = time.time()
        
        # Should complete reasonably quickly (under 1 second)
        assert end_time - start_time < 1.0
        assert result == sum(range(50))
    
    def test_repeated_large_dependency_calls(self):
        """Test performance of repeated calls with many dependencies."""
        registry = Registry()
        type_factory.register_hook(registry)
        container = Container(registry)
        
        # Create 20 service types
        service_types = []
        for i in range(20):
            service_class = type(f"RepeatedService{i}", (), {
                "__init__": lambda self, value=i: setattr(self, "value", value)
            })
            service_types.append(service_class)
            container.add(service_class())
        
        annotations = {f"service_{i}": Inject[service_types[i]] for i in range(20)}
        
        @injectable
        def compute_sum(**services):
            return sum(service.value for service in services.values())
        
        compute_sum.__annotations__ = annotations
        
        # First call (cold)
        start_time = time.time()
        result1 = container.call(compute_sum)
        first_call_time = time.time() - start_time
        
        # Subsequent calls (warm)
        call_times = []
        for _ in range(10):
            start_time = time.time()
            result = container.call(compute_sum)
            call_times.append(time.time() - start_time)
            assert result == result1  # Results should be consistent
        
        avg_warm_time = sum(call_times) / len(call_times)
        
        # Warm calls should be significantly faster than cold call
        assert avg_warm_time < first_call_time
        assert avg_warm_time < 0.1  # Should be very fast
    
    def test_wide_dependency_graph(self):
        """Test performance with wide dependency graphs (many services at same level)."""
        registry = Registry()
        type_factory.register_hook(registry)
        container = Container(registry)
        
        # Create many independent services
        base_services = []
        for i in range(30):
            service_class = type(f"BaseService{i}", (), {
                "__init__": lambda self, id=i: setattr(self, "id", id),
                "process": lambda self: f"processed-{self.id}"
            })
            base_services.append(service_class)
            container.add(service_class())
        
        # Create a service that depends on all base services
        class AggregatorService:
            def __init__(self, **services):
                self.services = services
            
            def aggregate(self):
                return [service.process() for service in self.services.values()]
        
        # Build annotations dynamically
        aggregator_annotations = {f"service_{i}": Inject[base_services[i]] for i in range(30)}
        
        @injectable
        def create_aggregator(**services):
            return AggregatorService(**services)
        
        create_aggregator.__annotations__ = aggregator_annotations
        
        start_time = time.time()
        aggregator = container.call(create_aggregator)
        end_time = time.time()
        
        # Should complete quickly
        assert end_time - start_time < 0.5
        
        # Verify functionality
        results = aggregator.aggregate()
        assert len(results) == 30
        assert all("processed-" in result for result in results)


class TestNestedDependencyChains:
    """Test performance with deep dependency chains."""
    
    def test_nested_dependency_resolution(self):
        """Test performance with nested dependency chains."""
        registry = Registry()
        type_factory.register_hook(registry)
        container = Container(registry)
        
        # Create a chain: A -> B -> C -> D -> E
        class ServiceE:
            def __init__(self):
                self.name = "E"
        
        class ServiceD:
            def __init__(self, e: ServiceE):
                self.e = e
                self.name = "D"
        
        class ServiceC:
            def __init__(self, d: ServiceD):
                self.d = d
                self.name = "C"
        
        class ServiceB:
            def __init__(self, c: ServiceC):
                self.c = c
                self.name = "B"
        
        class ServiceA:
            def __init__(self, b: ServiceB):
                self.b = b
                self.name = "A"
        
        @injectable
        def use_nested_service(service: Inject[ServiceA]):
            return f"{service.name}->{service.b.name}->{service.b.c.name}->{service.b.c.d.name}->{service.b.c.d.e.name}"
        
        start_time = time.time()
        result = container.call(use_nested_service)
        end_time = time.time()
        
        # Should complete quickly and return correct chain
        assert end_time - start_time < 0.1
        assert result == "A->B->C->D->E"
    
    def test_diamond_dependency_pattern(self):
        """Test performance with diamond dependency patterns."""
        registry = Registry()
        type_factory.register_hook(registry)
        container = Container(registry)
        
        # Create diamond pattern: A -> B,C -> D
        class ServiceD:
            def __init__(self):
                self.name = "D"
        
        class ServiceB:
            def __init__(self, d: ServiceD):
                self.d = d
                self.name = "B"
        
        class ServiceC:
            def __init__(self, d: ServiceD):
                self.d = d
                self.name = "C"
        
        class ServiceA:
            def __init__(self, b: ServiceB, c: ServiceC):
                self.b = b
                self.c = c
                self.name = "A"
        
        @injectable
        def use_diamond_service(service: Inject[ServiceA]):
            # Verify that B and C share the same D instance
            same_d = service.b.d is service.c.d
            return f"{service.name} with shared D: {same_d}"
        
        start_time = time.time()
        result = container.call(use_diamond_service)
        end_time = time.time()
        
        assert end_time - start_time < 0.1
        assert "A with shared D: True" in result
    
    def test_complex_dependency_web(self):
        """Test performance with complex interdependent services."""
        registry = Registry()
        type_factory.register_hook(registry)
        container = Container(registry)
        
        # Create a more complex web of dependencies
        class Database:
            def __init__(self):
                self.name = "Database"
        
        class Cache:
            def __init__(self, db: Database):
                self.db = db
                self.name = "Cache"
        
        class Logger:
            def __init__(self):
                self.name = "Logger"
        
        class UserRepository:
            def __init__(self, db: Database, cache: Cache, logger: Logger):
                self.db = db
                self.cache = cache
                self.logger = logger
                self.name = "UserRepository"
        
        class EmailService:
            def __init__(self, logger: Logger):
                self.logger = logger
                self.name = "EmailService"
        
        class UserService:
            def __init__(self, repo: UserRepository, email: EmailService, logger: Logger):
                self.repo = repo
                self.email = email
                self.logger = logger
                self.name = "UserService"
        
        @injectable
        def use_complex_service(service: Inject[UserService]):
            # Verify all dependencies are properly wired
            checks = [
                service.name == "UserService",
                service.repo.name == "UserRepository",
                service.email.name == "EmailService",
                service.repo.db.name == "Database",
                service.repo.cache.name == "Cache",
                # Logger should be shared across services
                service.logger is service.repo.logger,
                service.logger is service.email.logger,
                # Database should be shared between repo and cache
                service.repo.db is service.repo.cache.db
            ]
            return all(checks)
        
        start_time = time.time()
        result = container.call(use_complex_service)
        end_time = time.time()
        
        assert end_time - start_time < 0.2
        assert result is True


class TestFactoryPerformance:
    """Test performance characteristics of factories."""
    
    def test_factory_vs_direct_instance_performance(self):
        """Compare performance of factory vs direct instance injection."""
        registry = Registry()
        type_factory.register_hook(registry)
        container = Container(registry)
        
        # Direct instance
        class DirectService:
            def __init__(self):
                self.name = "direct"
        
        container.add(DirectService())
        
        # Factory-created service
        class FactoryService:
            def __init__(self):
                self.name = "factory"
        
        def factory_creator():
            return FactoryService()
        
        @injectable
        def use_direct(service: Inject[DirectService]):
            return service.name
        
        @injectable
        def use_factory(service: Inject[FactoryService, Options(default_factory=factory_creator)]):
            return service.name
        
        # Warm up
        container.call(use_direct)
        container.call(use_factory)
        
        # Measure direct instance calls
        direct_times = []
        for _ in range(100):
            start = time.time()
            container.call(use_direct)
            direct_times.append(time.time() - start)
        
        # Measure factory calls (should be cached after first call)
        factory_times = []
        for _ in range(100):
            start = time.time()
            container.call(use_factory)
            factory_times.append(time.time() - start)
        
        avg_direct = sum(direct_times) / len(direct_times)
        avg_factory = sum(factory_times) / len(factory_times)
        
        # Factory calls should be comparable to direct instances (due to caching)
        assert avg_factory < avg_direct * 2  # At most 2x slower
    
    def test_uncached_factory_performance(self):
        """Test performance impact of uncached factories."""
        registry = Registry()
        container = Container(registry)
        
        creation_count = 0
        
        def expensive_factory():
            nonlocal creation_count
            creation_count += 1
            time.sleep(0.001)  # Simulate expensive creation
            return type("ExpensiveService", (), {"id": creation_count})()
        
        @injectable
        def use_uncached_factory(service: Inject[object, Options(
            default_factory=expensive_factory,
            cache_factory_result=False
        )]):
            return service.id
        
        # Multiple calls should each create new instance
        start_time = time.time()
        results = []
        for _ in range(10):
            result = container.call(use_uncached_factory)
            results.append(result)
        end_time = time.time()
        
        # Should have created 10 instances
        assert creation_count == 10
        assert results == list(range(1, 11))
        
        # Should complete in reasonable time despite uncached creation
        assert end_time - start_time < 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])