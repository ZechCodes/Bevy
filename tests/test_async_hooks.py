import asyncio
import contextvars
import pytest
import time
from typing import Annotated
from unittest.mock import Mock

from tramp.optionals import Optional

from bevy import Inject, injectable
from bevy.hooks import hooks, Hook
from bevy.registries import Registry
from bevy.containers import Container
from bevy.context_vars import global_container
from bevy.factories import create_type_factory


class TestValue:
    def __init__(self, value: str):
        self.value = value


class TestDependency:
    def __init__(self, name: str = "test"):
        self.name = name


# Test contextvar for propagation verification
test_context_var: contextvars.ContextVar[str] = contextvars.ContextVar('test_context', default="")


@pytest.mark.asyncio
async def test_async_hook_basic():
    """Test that async hooks are called and executed properly."""
    called = []
    
    @hooks.GET_INSTANCE
    async def async_hook(container, dependency, context):
        await asyncio.sleep(0.01)  # Simulate async work
        called.append(True)
        return Optional.Some(TestValue("async_result"))
    
    registry = Registry()
    async_hook.register_hook(registry)
    container = registry.create_container()
    
    result = container.get(TestValue)
    assert isinstance(result, TestValue)
    assert result.value == "async_result"
    assert len(called) == 1


@pytest.mark.asyncio
async def test_async_hook_with_context_propagation():
    """Test that contextvars are properly propagated to async hooks."""
    captured_value = []
    
    @hooks.GET_INSTANCE
    async def async_hook_with_context(container, dependency, context):
        await asyncio.sleep(0.01)
        # Capture the context var value in the async thread
        captured_value.append(test_context_var.get())
        return Optional.Some(TestValue("with_context"))
    
    registry = Registry()
    async_hook_with_context.register_hook(registry)
    container = registry.create_container()
    
    # Set context var in main thread
    test_context_var.set("main_thread_value")
    
    result = container.get(TestValue)
    assert isinstance(result, TestValue)
    assert result.value == "with_context"
    
    # Verify context was propagated
    assert captured_value[0] == "main_thread_value"


def test_mixed_sync_async_hooks():
    """Test that sync and async hooks can coexist."""
    call_order = []
    
    @hooks.CREATE_INSTANCE
    def sync_hook(container, dependency, context):
        call_order.append("sync_create")
        return Optional.Nothing()
    
    @hooks.GET_INSTANCE
    async def async_hook(container, dependency, context):
        await asyncio.sleep(0.01)
        call_order.append("async_get")
        return Optional.Nothing()
    
    @hooks.CREATED_INSTANCE
    def sync_filter(container, instance, context):
        call_order.append("sync_filter")
        return Optional.Some(instance)
    
    registry = Registry()
    registry.add_factory(create_type_factory(TestDependency))
    sync_hook.register_hook(registry)
    async_hook.register_hook(registry)
    sync_filter.register_hook(registry)
    
    container = registry.create_container()
    result = container.get(TestDependency)
    
    assert isinstance(result, TestDependency)
    assert "sync_create" in call_order
    assert "async_get" in call_order
    assert "sync_filter" in call_order


def test_async_hook_timeout_handling():
    """Test that async hooks handle timeouts properly."""
    
    @hooks.GET_INSTANCE
    async def slow_async_hook(container, dependency, context):
        # This should timeout (default is 30 seconds in our implementation)
        await asyncio.sleep(35)
        return Optional.Some(TestValue("should_timeout"))
    
    registry = Registry()
    slow_async_hook.register_hook(registry)
    container = registry.create_container()
    
    # This should raise a timeout error
    with pytest.raises(TimeoutError) as exc_info:
        container.get(TestValue)
    
    assert "timed out" in str(exc_info.value)


def test_async_hook_exception_propagation():
    """Test that exceptions in async hooks are properly propagated."""
    
    @hooks.GET_INSTANCE
    async def failing_async_hook(container, dependency, context):
        await asyncio.sleep(0.01)
        raise ValueError("Async hook failed")
    
    registry = Registry()
    failing_async_hook.register_hook(registry)
    container = registry.create_container()
    
    with pytest.raises(ValueError) as exc_info:
        container.get(TestValue)
    
    assert "Async hook failed" in str(exc_info.value)


def test_async_hook_with_injection():
    """Test async hooks in injection context."""
    hook_called = []
    
    @hooks.INJECTION_REQUEST
    async def async_injection_hook(container, context):
        await asyncio.sleep(0.01)
        hook_called.append(context.parameter_name)
        return Optional.Nothing()
    
    @injectable
    def test_func(dep: Inject[TestDependency]):
        return dep.name
    
    registry = Registry()
    registry.add_factory(create_type_factory(TestDependency))
    async_injection_hook.register_hook(registry)
    
    container = registry.create_container()
    result = container.call(test_func)
    
    assert result == "test"
    assert "dep" in hook_called


def test_async_hook_filter():
    """Test async hooks with filter behavior."""
    
    @hooks.CREATED_INSTANCE
    async def async_filter_hook(container, instance, context):
        await asyncio.sleep(0.01)
        if isinstance(instance, TestDependency):
            instance.name = "filtered_async"
        return Optional.Some(instance)
    
    registry = Registry()
    registry.add_factory(create_type_factory(TestDependency))
    async_filter_hook.register_hook(registry)
    
    container = registry.create_container()
    result = container.get(TestDependency)
    
    assert result.name == "filtered_async"


def test_multiple_async_hooks():
    """Test multiple async hooks with different hook types work together."""
    hooks_called = []
    
    @hooks.CREATE_INSTANCE
    async def create_hook(container, dependency, context):
        await asyncio.sleep(0.01)
        if dependency == TestValue:
            hooks_called.append("create")
            return Optional.Some(TestValue("created"))
        return Optional.Nothing()
    
    @hooks.CREATED_INSTANCE  
    async def filter_hook(container, instance, context):
        await asyncio.sleep(0.01)
        if isinstance(instance, TestValue):
            hooks_called.append("filter")
            instance.value = "filtered"
            return Optional.Some(instance)
        return Optional.Nothing()
    
    registry = Registry()
    create_hook.register_hook(registry)
    filter_hook.register_hook(registry)
    
    container = registry.create_container()
    result = container.get(TestValue)
    
    assert isinstance(result, TestValue)
    assert result.value == "filtered"
    # Both hooks should have been called
    assert set(hooks_called) == {"create", "filter"}


def test_async_hook_with_legacy_signature():
    """Test async hooks with legacy 2-parameter signature."""
    
    @hooks.GET_INSTANCE
    async def legacy_async_hook(container, dependency):
        # Legacy style without context parameter
        await asyncio.sleep(0.01)
        return Optional.Some(TestValue("legacy_async"))
    
    registry = Registry()
    legacy_async_hook.register_hook(registry)
    container = registry.create_container()
    
    result = container.get(TestValue)
    assert isinstance(result, TestValue)
    assert result.value == "legacy_async"


def test_async_post_injection_hook():
    """Test async hooks for post-injection callbacks."""
    post_hook_called = []
    
    @hooks.POST_INJECTION_CALL
    async def async_post_hook(container, context):
        await asyncio.sleep(0.01)
        post_hook_called.append({
            'function': context.function_name,
            'result': context.result
        })
        return Optional.Nothing()
    
    @injectable
    def test_func(dep: Inject[TestDependency]):
        return f"Result: {dep.name}"
    
    registry = Registry()
    registry.add_factory(create_type_factory(TestDependency))
    async_post_hook.register_hook(registry)
    
    container = registry.create_container()
    result = container.call(test_func)
    
    assert result == "Result: test"  # Default TestDependency has name="test"
    assert len(post_hook_called) == 1
    assert post_hook_called[0]['function'] == 'test_func'
    assert post_hook_called[0]['result'] == "Result: test"


def test_async_hook_with_parent_container():
    """Test async hooks with parent container inheritance."""
    
    @hooks.GET_INSTANCE
    async def parent_async_hook(container, dependency, context):
        await asyncio.sleep(0.01)
        if dependency == TestValue:
            return Optional.Some(TestValue("from_parent"))
        return Optional.Nothing()
    
    parent_registry = Registry()
    parent_async_hook.register_hook(parent_registry)
    parent_container = parent_registry.create_container()
    
    child_container = parent_container.branch()
    
    result = child_container.get(TestValue)
    assert isinstance(result, TestValue)
    assert result.value == "from_parent"


def test_contextvar_chain_propagation():
    """Test that injection chain contextvar is propagated to async hooks."""
    captured_chain = []
    
    @hooks.INJECTION_REQUEST
    async def capture_chain_hook(container, context):
        await asyncio.sleep(0.01)
        # The injection chain should be preserved
        captured_chain.append(list(context.injection_chain))
        return Optional.Nothing()
    
    @injectable
    def outer_func(inner: Inject[TestDependency]):
        return inner
    
    @injectable
    def inner_func(dep: Inject[TestDependency]):
        return dep
    
    registry = Registry()
    registry.add_factory(create_type_factory(TestDependency))
    capture_chain_hook.register_hook(registry)
    
    container = registry.create_container()
    container.call(outer_func)
    
    # Should have captured the injection chain
    assert len(captured_chain) > 0


def test_async_hook_concurrent_execution():
    """Test that async hooks handle concurrent calls properly."""
    results = []
    
    @hooks.GET_INSTANCE
    async def concurrent_hook(container, dependency, context):
        await asyncio.sleep(0.01)
        import random
        value = random.randint(1, 1000)
        return Optional.Some(TestValue(str(value)))
    
    registry = Registry()
    concurrent_hook.register_hook(registry)
    container = registry.create_container()
    
    # Make multiple concurrent calls
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(container.get, TestValue) for _ in range(5)]
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            results.append(result)
    
    # All results should be TestValue instances
    assert len(results) == 5
    assert all(isinstance(r, TestValue) for r in results)