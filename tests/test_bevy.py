import os
from functools import wraps
from unittest import mock

import pytest
from pytest import raises
from tramp.optionals import Optional

from bevy import auto_inject, get_container, get_registry, Inject, injectable, Registry
from bevy.bundled.type_factory_hook import type_factory
from bevy.context_vars import GlobalContextDisabledError
from bevy.factories import create_type_factory
from bevy.hooks import Hook, hooks
from bevy.injection_types import Options


class DummyObject:
    def __init__(self, value=None):
        self.value = value


def test_containers():
    registry = Registry()
    registry.add_factory(create_type_factory(DummyObject))
    container = registry.create_container()

    instance = container.get(DummyObject)
    assert isinstance(instance, DummyObject)
    assert container.get(DummyObject) is instance


def test_inherit_from_parent_container():
    registry = Registry()
    registry.add_factory(create_type_factory(DummyObject))

    parent = registry.create_container()
    child = parent.branch()

    instance = parent.get(DummyObject)
    assert child.get(DummyObject) is instance


def test_child_overrides_parent_container():
    registry = Registry()
    registry.add_factory(create_type_factory(DummyObject))

    parent = registry.create_container()
    child = parent.branch()

    child_instance = child.get(DummyObject)
    parent_instance = parent.get(DummyObject)
    assert child_instance is not parent_instance
    assert child_instance is child.get(DummyObject)
    assert parent_instance is parent.get(DummyObject)


def test_injection():
    @injectable
    def test(d: Inject[DummyObject]):
        assert isinstance(d, DummyObject)

    registry = Registry()
    registry.add_factory(create_type_factory(DummyObject))
    container = registry.create_container()
    container.call(test)


def test_injection_wrapper():
    @auto_inject
    @injectable
    def test(d: Inject[DummyObject]):
        assert isinstance(d, DummyObject)

    with Registry() as registry:
        registry.add_factory(create_type_factory(DummyObject))

        test()


def test_injection_factories():
    from bevy import Options
    
    @auto_inject
    @injectable
    def test(d: Inject[DummyObject, Options(default_factory=lambda: DummyObject("a"))]):
        assert isinstance(d, DummyObject) and d.value == "a"

    with Registry() as registry:
        test()


def test_get_instance_hook():
    values = ["a", "b"]
    index = 0
    def hook(_, dependency_type, __):
        nonlocal index
        if dependency_type is DummyObject:
            old_index, index = index, index + 1
            return Optional.Some(DummyObject(values[old_index]))

        return Optional.Nothing()

    registry = Registry()
    registry.add_hook(Hook.GET_INSTANCE, hook)
    container = registry.create_container()

    assert container.get(DummyObject).value == values[0]
    assert container.get(DummyObject).value == values[1]


def test_create_instance_hook():
    values = ["a", "b"]
    index = 0
    def hook(_, dependency_type, __):
        nonlocal index
        if dependency_type is DummyObject:
            old_index, index = index, index + 1
            value = DummyObject(values[old_index])
            container.add(dependency_type, value)
            return Optional.Some(value)

        return Optional.Nothing()

    registry = Registry()
    registry.add_hook(Hook.CREATE_INSTANCE, hook)
    container = registry.create_container()

    assert container.get(DummyObject).value == values[0]
    assert container.get(DummyObject).value == values[0]


def test_created_instance_hook():
    runs = 0
    def hook(_, value, __):
        nonlocal runs
        if isinstance(value, DummyObject):
            runs += 1

    registry = Registry()
    registry.add_factory(create_type_factory(DummyObject))
    registry.add_hook(Hook.CREATED_INSTANCE, hook)

    container = registry.create_container()
    container.get(DummyObject)
    container.get(DummyObject)

    assert runs == 1


def test_got_instance_hook():
    runs = 0
    def hook(_, value, __):
        nonlocal runs
        if isinstance(value, DummyObject):
            runs += 1

    registry = Registry()
    registry.add_factory(create_type_factory(DummyObject))
    registry.add_hook(Hook.GOT_INSTANCE, hook)

    container = registry.create_container()
    container.get(DummyObject)
    container.get(DummyObject)

    assert runs == 2


def test_unsupported_dependency_hook():
    @hooks.HANDLE_UNSUPPORTED_DEPENDENCY
    def hook(_, dependency_type, __):
        if dependency_type is DummyObject:
            return Optional.Some(DummyObject("a"))

        return Optional.Nothing()

    registry = Registry()
    hook.register_hook(registry)
    container = registry.create_container()

    assert container.get(DummyObject).value == "a"


def test_type_factory_hook():
    registry = Registry()
    type_factory.register_hook(registry)

    container = registry.create_container()
    assert isinstance(container.get(DummyObject), DummyObject)


def test_type_init_injection():
    class Dep:
        @injectable
        def __init__(self, value: Inject[DummyObject]):
            self.obj = value

    with Registry() as outer_registry:
        outer_registry.add_factory(create_type_factory(DummyObject))

        with outer_registry.create_container() as outer_container:
            outer_dummy = outer_container.get(DummyObject)

            registry = Registry()
            registry.add_factory(create_type_factory(DummyObject, 100))
            container = registry.create_container()
            inner_dummy = container.call(Dep).obj
            assert inner_dummy.value == 100
            assert inner_dummy is not outer_dummy


@mock.patch.dict(os.environ, {"BEVY_ENABLE_GLOBAL_CONTEXT": "False"})
def test_no_global_context():
    with raises(GlobalContextDisabledError):
        get_registry()

    with raises(GlobalContextDisabledError):
        get_container()


def test_positional_only_injection():
    @auto_inject
    @injectable
    def test(a: Inject[DummyObject], /):
        assert isinstance(a, DummyObject)

    with Registry().create_container() as container:
        container.add(DummyObject())
        test()


@pytest.mark.xfail(reason="Positional-only parameter with conflicting kwarg handling may vary across environments")
def test_positional_only_with_conflicting_kwarg():
    @auto_inject
    @injectable
    def test(a: Inject[DummyObject], /, **kwargs):
        assert kwargs == {"a": "foobar"}
        assert isinstance(a, DummyObject)

    with Registry().create_container() as container:
        container.add(DummyObject())
        test(a="foobar")


def test_method_injection_with_positional_only():
    class Test:
        @auto_inject
        @injectable
        def test(self, a: Inject[DummyObject], /):
            assert isinstance(a, DummyObject)

    with Registry().create_container() as container:
        container.add(DummyObject())
        Test().test()


@pytest.mark.xfail(
    reason="Bevy does not currently support injection into wrapping decorators."
)
def test_decorators():
    injections = set()

    def decorator(func):
        @auto_inject
        @injectable
        @wraps(func)
        def wrapper(a: Inject[DummyObject]):
            injections.add(f"wrapper({id(a)} {type(a).__name__})")
            return func(a)

        return wrapper

    @auto_inject
    @injectable
    @decorator
    def test(a: Inject[DummyObject]):
        injections.add(f"test({id(a)} {type(a).__name__})")

    with Registry().create_container() as container:
        container.add(obj := DummyObject())
        test()

        assert injections == {f"test({id(obj)} DummyObject)", f"wrapper({id(obj)} DummyObject)"}


def test_container_find_basic():
    """Test that container.find() returns a Result that can be resolved."""
    registry = Registry()
    registry.add_factory(create_type_factory(DummyObject))
    container = registry.create_container()

    result = container.find(DummyObject)
    instance = result.get()

    assert isinstance(instance, DummyObject)
    assert container.get(DummyObject) is instance


def test_container_find_with_default():
    """Test that container.find() with default works."""
    registry = Registry()
    container = registry.create_container()

    default_obj = DummyObject("default")
    result = container.find(DummyObject, default=default_obj)
    instance = result.get()

    assert instance is default_obj


def test_container_find_with_default_factory():
    """Test that container.find() with default_factory works."""
    registry = Registry()
    container = registry.create_container()

    result = container.find(DummyObject, default_factory=lambda: DummyObject("factory"))
    instance = result.get()

    assert isinstance(instance, DummyObject)
    assert instance.value == "factory"


def test_container_find_with_qualifier():
    """Test that container.find() with qualifier works."""
    registry = Registry()
    container = registry.create_container()

    obj1 = DummyObject("qualified")
    container.add(DummyObject, obj1, qualifier="special")

    result = container.find(DummyObject, qualifier="special")
    instance = result.get()

    assert instance is obj1


@pytest.mark.asyncio
async def test_container_find_async():
    """Test that container.find() can be awaited in async context."""
    registry = Registry()
    registry.add_factory(create_type_factory(DummyObject))
    container = registry.create_container()

    result = container.find(DummyObject)
    instance = await result  # Using __await__

    assert isinstance(instance, DummyObject)


@pytest.mark.asyncio
async def test_container_find_get_async():
    """Test that container.find().get_async() works."""
    registry = Registry()
    registry.add_factory(create_type_factory(DummyObject))
    container = registry.create_container()

    result = container.find(DummyObject)
    instance = await result.get_async()

    assert isinstance(instance, DummyObject)
    assert container.get(DummyObject) is instance


@pytest.mark.asyncio
async def test_container_find_uses_async_hooks():
    """Test that container.find() uses async hooks, not sync wrappers."""
    from bevy.hooks import Hook
    import asyncio

    hook_called = False
    hook_thread_id = None
    main_thread_id = asyncio.current_task()

    async def async_create_hook(container, dependency, context):
        nonlocal hook_called, hook_thread_id
        hook_called = True
        hook_thread_id = asyncio.current_task()
        # Simulate async work
        await asyncio.sleep(0.001)
        if dependency is DummyObject:
            return Optional.Some(DummyObject("async_hook"))
        return Optional.Nothing()

    registry = Registry()
    registry.add_hook(Hook.CREATE_INSTANCE, async_create_hook)
    container = registry.create_container()

    result = container.find(DummyObject)
    instance = await result.get_async()

    assert hook_called, "Async hook should have been called"
    assert instance.value == "async_hook"
    # Verify we're in the same async context (not wrapped in a thread)
    assert hook_thread_id == main_thread_id, "Hook should run in same async context"


@pytest.mark.asyncio
async def test_async_function_injection_basic():
    """Test that async functions can be injected with dependencies."""
    @injectable
    async def async_func(obj: Inject[DummyObject]):
        return obj.value

    registry = Registry()
    registry.add_factory(create_type_factory(DummyObject))
    container = registry.create_container()

    coro = container.call(async_func)
    result = await coro

    assert result is None  # DummyObject() has value=None by default


@pytest.mark.asyncio
async def test_async_function_with_async_hooks():
    """Test that async functions use async hooks during injection."""
    from bevy.hooks import Hook
    import asyncio

    hook_called = []

    async def async_create_hook(container, dependency, context):
        await asyncio.sleep(0.001)
        hook_called.append(dependency.__name__)
        if dependency is DummyObject:
            return Optional.Some(DummyObject("from_hook"))
        return Optional.Nothing()

    @injectable
    async def async_func(obj: Inject[DummyObject]):
        return obj.value

    registry = Registry()
    registry.add_hook(Hook.CREATE_INSTANCE, async_create_hook)
    container = registry.create_container()

    result = await container.call(async_func)

    assert result == "from_hook"
    assert "DummyObject" in hook_called


@pytest.mark.asyncio
async def test_async_function_with_qualified_dependency():
    """Test async function injection with qualified dependencies."""
    @injectable
    async def async_func(obj: Inject[DummyObject, Options(qualifier="special")]):
        return obj.value

    registry = Registry()
    container = registry.create_container()

    special_obj = DummyObject("special_value")
    container.add(DummyObject, special_obj, qualifier="special")

    result = await container.call(async_func)

    assert result == "special_value"


@pytest.mark.asyncio
async def test_async_function_with_default_factory():
    """Test async function injection with default_factory."""
    @injectable
    async def async_func(obj: Inject[DummyObject, Options(default_factory=lambda: DummyObject("factory"))]):
        return obj.value

    registry = Registry()
    container = registry.create_container()

    result = await container.call(async_func)

    assert result == "factory"


@pytest.mark.asyncio
async def test_async_function_with_cache_factory_result_false():
    """Test async function injection with cache_factory_result=False."""
    call_count = [0]

    def factory():
        call_count[0] += 1
        return DummyObject(f"call_{call_count[0]}")

    @injectable
    async def async_func(obj: Inject[DummyObject, Options(default_factory=factory, cache_factory_result=False)]):
        return obj.value

    registry = Registry()
    container = registry.create_container()

    result1 = await container.call(async_func)
    result2 = await container.call(async_func)

    assert result1 == "call_1"
    assert result2 == "call_2"  # Should be different instances


@pytest.mark.asyncio
async def test_async_function_returns_coroutine():
    """Test that calling async function returns coroutine."""
    import inspect

    @injectable
    async def async_func(obj: Inject[DummyObject]):
        return obj.value

    registry = Registry()
    registry.add_factory(create_type_factory(DummyObject))
    container = registry.create_container()

    result = container.call(async_func)

    assert inspect.iscoroutine(result), "Should return coroutine"
    await result  # Clean up


@pytest.mark.asyncio
async def test_sync_and_async_functions_share_dependencies():
    """Test that sync and async functions can share the same dependency instances."""
    @injectable
    def sync_func(obj: Inject[DummyObject]):
        return obj

    @injectable
    async def async_func(obj: Inject[DummyObject]):
        return obj

    registry = Registry()
    registry.add_factory(create_type_factory(DummyObject))
    container = registry.create_container()

    sync_result = container.call(sync_func)
    async_result = await container.call(async_func)

    assert sync_result is async_result, "Should be the same cached instance"
