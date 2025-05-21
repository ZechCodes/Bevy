from typing import Annotated

import pytest
from tramp.optionals import Optional

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
@pytest.mark.parametrize("hook", [hooks.CREATE_INSTANCE, hooks.HANDLE_UNSUPPORTED_DEPENDENCY])
def test_create_instance(dep, hook):
    @hooks.CREATE_INSTANCE
    def hook(container, dependency):
        return Optional.Some(InjectWrapper(dependency))

    registry = Registry()
    hook.register_hook(registry)
    container = registry.create_container()
    result = container.get(dep)
    assert isinstance(result, InjectWrapper)
    assert result.dep is dep


@pytest.mark.parametrize("dep", type_parameters)
def test_get_instance(dep):
    @hooks.GET_INSTANCE
    def hook(container, dependency):
        return Optional.Some(InjectWrapper(dependency))

    registry = Registry()
    hook.register_hook(registry)
    container = registry.create_container()
    result = container.get(dep)
    assert isinstance(result, InjectWrapper)
