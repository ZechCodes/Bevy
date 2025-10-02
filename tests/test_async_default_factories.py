"""
Test async default factory support in bevy dependency injection.

These tests verify that async factories work in all contexts:
- Direct container.get() calls (sync and async)
- Dependency injection in sync functions
- Dependency injection in async functions
- Factory caching behavior
"""
import asyncio

import pytest
from bevy import Container, Inject, injectable, Registry
from bevy.injection_types import Options


# Test fixtures - simple counter classes
class Counter:
    """Simple service for testing factory calls."""
    _instance_count = 0

    def __init__(self, value: int = 0):
        Counter._instance_count += 1
        self.value = value
        self.id = Counter._instance_count

    @classmethod
    def reset_count(cls):
        cls._instance_count = 0


class Dependency:
    """Dependency that can be injected into factories."""
    def __init__(self, name: str = "dep"):
        self.name = name


# Sync and async factory functions
def sync_counter_factory() -> Counter:
    """Synchronous factory."""
    return Counter(value=42)


async def async_counter_factory() -> Counter:
    """Async factory that awaits."""
    await asyncio.sleep(0.001)  # Simulate async work
    return Counter(value=99)


@injectable
async def async_factory_with_deps(dep: Inject[Dependency]) -> Counter:
    """Async factory that requires dependency injection."""
    await asyncio.sleep(0.001)
    return Counter(value=len(dep.name))


@pytest.fixture
def registry():
    """Fresh registry for each test."""
    return Registry()


@pytest.fixture
def container(registry):
    """Fresh container for each test."""
    Counter.reset_count()
    return Container(registry)


# ============================================================================
# Test 1: Async factory in async context (direct call)
# ============================================================================

@pytest.mark.asyncio
async def test_async_factory_in_async_context_direct(container):
    """Async factory should work with await container.find().get_async()."""
    result = await container.find(
        Counter,
        default_factory=async_counter_factory
    ).get_async()

    assert isinstance(result, Counter)
    assert result.value == 99
    assert result.id == 1


# ============================================================================
# Test 2: Async factory in sync context (direct call)
# ============================================================================

def test_async_factory_in_sync_context_direct(container):
    """Async factory should work with container.get() in sync code."""
    result = container.get(Counter, default_factory=async_counter_factory)

    assert isinstance(result, Counter)
    assert result.value == 99
    assert result.id == 1


# ============================================================================
# Test 3: Async factory via injection in async function
# ============================================================================

@pytest.mark.asyncio
async def test_async_factory_via_injection_async_function(container):
    """Async factory should work when injected into async function."""

    @injectable
    async def async_consumer(
        counter: Inject[Counter, Options(default_factory=async_counter_factory)]
    ) -> int:
        return counter.value

    result = await container.call(async_consumer)

    assert result == 99


# ============================================================================
# Test 4: Async factory via injection in sync function
# ============================================================================

def test_async_factory_via_injection_sync_function(container):
    """Async factory should work when injected into sync function."""

    @injectable
    def sync_consumer(
        counter: Inject[Counter, Options(default_factory=async_counter_factory)]
    ) -> int:
        return counter.value

    result = container.call(sync_consumer)

    assert result == 99


# ============================================================================
# Test 5: Sync factory still works (regression test)
# ============================================================================

def test_sync_factory_still_works(container):
    """Ensure sync factories continue to work after changes."""
    result = container.get(Counter, default_factory=sync_counter_factory)

    assert isinstance(result, Counter)
    assert result.value == 42
    assert result.id == 1


@pytest.mark.asyncio
async def test_sync_factory_in_async_context(container):
    """Sync factories should work in async context too."""
    result = await container.find(
        Counter,
        default_factory=sync_counter_factory
    ).get_async()

    assert isinstance(result, Counter)
    assert result.value == 42


# ============================================================================
# Test 6: Async factory with dependencies
# ============================================================================

@pytest.mark.asyncio
async def test_async_factory_with_dependency_injection(container):
    """Async factory should support dependency injection via container.call()."""
    # Add dependency to container
    container.add(Dependency("test"))

    result = await container.find(
        Counter,
        default_factory=async_factory_with_deps
    ).get_async()

    assert isinstance(result, Counter)
    assert result.value == 4  # len("test")


# ============================================================================
# Test 7: Factory caching behavior
# ============================================================================

def test_async_factory_caching_enabled(container):
    """With cache_factory_result=True, factory should only be called once."""
    Counter.reset_count()

    # First call
    result1 = container.get(Counter, default_factory=async_counter_factory)
    assert result1.id == 1

    # Second call - should return cached instance
    result2 = container.get(Counter, default_factory=async_counter_factory)
    assert result2.id == 1  # Same instance
    assert result1 is result2


@pytest.mark.asyncio
async def test_async_factory_caching_disabled(container):
    """With cache_factory_result=False, factory should be called each time."""
    Counter.reset_count()

    @injectable
    async def consumer(
        c1: Inject[Counter, Options(
            default_factory=async_counter_factory,
            cache_factory_result=False
        )],
        c2: Inject[Counter, Options(
            default_factory=async_counter_factory,
            cache_factory_result=False
        )]
    ) -> tuple[int, int]:
        return (c1.id, c2.id)

    id1, id2 = await container.call(consumer)

    # Should get different instances
    assert id1 == 1
    assert id2 == 2


# ============================================================================
# Test 8: Factory inheritance across container branches
# ============================================================================

def test_async_factory_cache_inherited_by_child_container(container):
    """Child containers should inherit parent's factory cache."""
    # Parent creates instance via factory
    result1 = container.get(Counter, default_factory=async_counter_factory)
    assert result1.id == 1

    # Child should reuse parent's cached result
    child = container.branch()
    result2 = child.get(Counter, default_factory=async_counter_factory)
    assert result2.id == 1
    assert result2 is result1


# ============================================================================
# Test 9: Error handling for async factory failures
# ============================================================================

@pytest.mark.asyncio
async def test_async_factory_propagates_exceptions():
    """Exceptions in async factories should propagate correctly."""

    async def failing_factory() -> Counter:
        await asyncio.sleep(0.001)
        raise ValueError("Factory failed!")

    container = Container(Registry())

    with pytest.raises(ValueError, match="Factory failed!"):
        await container.find(Counter, default_factory=failing_factory).get_async()


# ============================================================================
# Test 10: Mixed sync/async factories in same function
# ============================================================================

@pytest.mark.asyncio
async def test_mixed_sync_async_factories_in_same_function(container):
    """Should handle both sync and async factories in same function."""

    class OtherService:
        def __init__(self, val: int):
            self.val = val

    def sync_factory() -> OtherService:
        return OtherService(10)

    async def async_factory() -> OtherService:
        await asyncio.sleep(0.001)
        return OtherService(20)

    @injectable
    async def consumer(
        s1: Inject[OtherService, Options(default_factory=sync_factory, qualifier="sync")],
        s2: Inject[OtherService, Options(default_factory=async_factory, qualifier="async")]
    ) -> tuple[int, int]:
        return (s1.val, s2.val)

    v1, v2 = await container.call(consumer)
    assert v1 == 10
    assert v2 == 20
