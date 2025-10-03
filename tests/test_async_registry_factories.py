"""Test that registry.add_factory supports async factories."""

import asyncio
import pytest
from bevy import Container, Registry


class Service:
    def __init__(self, value: int):
        self.value = value


class AsyncService:
    def __init__(self, value: str):
        self.value = value


@pytest.mark.asyncio
async def test_async_factory_on_registry():
    """Test that async factories registered on registry work correctly."""
    
    async def async_factory(container):
        await asyncio.sleep(0.001)
        return Service(42)
    
    registry = Registry()
    registry.add_factory(async_factory, Service)
    container = Container(registry)
    
    service = await container.find(Service).get_async()
    assert service.value == 42


@pytest.mark.asyncio
async def test_sync_factory_on_registry():
    """Test that sync factories still work on registry."""
    
    def sync_factory(container):
        return Service(10)
    
    registry = Registry()
    registry.add_factory(sync_factory, Service)
    container = Container(registry)
    
    service = await container.find(Service).get_async()
    assert service.value == 10


@pytest.mark.asyncio
async def test_async_factory_with_dependency_injection():
    """Test async factory that uses dependency injection from container."""
    
    async def async_factory(container):
        config = container.get(Service)  # Get existing dependency
        await asyncio.sleep(0.001)
        return AsyncService(f"created-with-{config.value}")
    
    registry = Registry()
    registry.add_factory(async_factory, AsyncService)
    container = Container(registry)
    container.add(Service(100))
    
    service = await container.find(AsyncService).get_async()
    assert service.value == "created-with-100"


@pytest.mark.asyncio
async def test_async_factory_caching():
    """Test that async factories cache results properly."""
    call_count = 0
    
    async def counting_factory(container):
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.001)
        return Service(call_count)
    
    registry = Registry()
    registry.add_factory(counting_factory, Service)
    container = Container(registry)
    
    service1 = await container.find(Service).get_async()
    service2 = await container.find(Service).get_async()
    
    assert call_count == 1  # Factory called only once
    assert service1 is service2  # Same instance returned
    assert service1.value == 1


def test_async_factory_in_sync_context():
    """Test that async factories work in sync context via Result.get()."""
    
    async def async_factory(container):
        await asyncio.sleep(0.001)
        return Service(99)
    
    registry = Registry()
    registry.add_factory(async_factory, Service)
    container = Container(registry)
    
    # Sync get() should handle async factory via thread pool
    service = container.get(Service)
    assert service.value == 99


@pytest.mark.asyncio
async def test_mixed_sync_and_async_factories():
    """Test using both sync and async factories in the same registry."""
    
    async def async_factory(container):
        await asyncio.sleep(0.001)
        return Service(1)
    
    def sync_factory(container):
        return AsyncService("sync")
    
    registry = Registry()
    registry.add_factory(async_factory, Service)
    registry.add_factory(sync_factory, AsyncService)
    container = Container(registry)
    
    service = await container.find(Service).get_async()
    async_service = await container.find(AsyncService).get_async()
    
    assert service.value == 1
    assert async_service.value == "sync"
