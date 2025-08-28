from typing import Annotated

import pytest
from tramp.optionals import Optional

from bevy import Inject, injectable
from bevy.hooks import hooks
from bevy.registries import Registry


class InjectWrapper:
    def __init__(self, dep):
        self.dep = dep


class InjectClass:
    def __init__(self, payload):
        self.payload = payload


type_parameters = [InjectClass, Annotated[InjectClass, ...], InjectClass | None]


@pytest.mark.parametrize("dep", type_parameters)
@pytest.mark.parametrize("hook_type", [hooks.CREATE_INSTANCE, hooks.HANDLE_UNSUPPORTED_DEPENDENCY])
def test_create_instance(dep, hook_type):
    @hook_type
    def hook_func(container, dependency, context):
        return Optional.Some(InjectWrapper(dependency))

    registry = Registry()
    hook_func.register_hook(registry)
    container = registry.create_container()
    result = container.get(dep)
    assert isinstance(result, InjectWrapper)
    assert result.dep is dep


@pytest.mark.parametrize("dep", type_parameters)
def test_get_instance(dep):
    @hooks.GET_INSTANCE
    def hook(container, dependency, context):
        return Optional.Some(InjectWrapper(dependency))

    registry = Registry()
    hook.register_hook(registry)
    container = registry.create_container()
    result = container.get(dep)
    assert isinstance(result, InjectWrapper)


@pytest.mark.parametrize("hook_type", [hooks.CREATE_INSTANCE, hooks.GET_INSTANCE, hooks.HANDLE_UNSUPPORTED_DEPENDENCY])
def test_hooks_are_not_cached(hook_type):
    @hook_type
    def hook(container, dependency, context):
        return Optional.Some(InjectWrapper(dependency))

    registry = Registry()
    hook.register_hook(registry)
    container = registry.create_container()
    result1 = container.get(InjectClass)
    result2 = container.get(InjectClass)
    assert result1 is not result2


@pytest.mark.parametrize("hook_type", [hooks.CREATE_INSTANCE, hooks.GET_INSTANCE, hooks.HANDLE_UNSUPPORTED_DEPENDENCY])
def test_hooks_explicitly_cache(hook_type):
    @hook_type
    def hook(container, dependency, context):
        if dependency in container.instances:
            return Optional.Some(container.instances[dependency])

        value = InjectWrapper(dependency)
        container.add(dependency, value)
        return Optional.Some(value)

    registry = Registry()
    hook.register_hook(registry)
    container = registry.create_container()
    result1 = container.get(InjectClass)
    result2 = container.get(InjectClass)
    assert result1 is result2


@pytest.mark.parametrize("hook_type", [hooks.CREATE_INSTANCE, hooks.GET_INSTANCE, hooks.HANDLE_UNSUPPORTED_DEPENDENCY])
def test_hooks_can_modify(hook_type):
    @hook_type
    def hook(container, dependency, context):
        assert "injection_context" in context
        assert context["injection_context"].parameter_name == "dep"
        return Optional.Some(InjectWrapper(dependency))

    @injectable
    def test_func(dep: Inject[InjectClass]):
        pass

    registry = Registry()
    hook.register_hook(registry)
    container = registry.create_container()
    container.call(test_func)
