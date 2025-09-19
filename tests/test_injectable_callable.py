import functools

from bevy import auto_inject, injectable
from bevy.containers import Container
from bevy.registries import Registry
from bevy.injection_types import Inject


class Service:
    def __init__(self, name: str):
        self.name = name


class Dependency:
    def __init__(self, value: str):
        self.value = value


@auto_inject
@injectable
def use_service(service: Inject[Service]) -> str:
    return service.name


def test_auto_inject_prefers_calling_container():
    registry = Registry()
    global_container = Container(registry)

    with global_container:
        global_container.add(Service("global"))

        branch = global_container.branch()
        branch.add(Service("local"))

        # Direct call uses the global container
        assert use_service() == "global"

        # Calling through a container respects that container's overrides
        assert branch.call(use_service) == "local"


def test_auto_inject_with_additional_wrapper_uses_both_containers():
    captured = []

    def capture_decorator(fn):
        @functools.wraps(fn)
        def wrapper(service: Inject[Service]):
            captured.append(service.name)
            return fn(service=service)

        return wrapper

    @capture_decorator
    @auto_inject
    @injectable
    def wrapped(service: Inject[Service]) -> str:
        return service.name

    registry = Registry()
    global_container = Container(registry)

    with global_container:
        global_container.add(Service("global"))

        branch = global_container.branch()
        branch.add(Service("local"))

        result = branch.call(wrapped)

    assert result == "global"
    assert captured == ["local"], "Outer wrapper should see the calling container's dependency"


class Handler:
    def __init__(self, prefix: str):
        self.prefix = prefix

    @injectable
    def instance_call(self, dep: Inject[Dependency]) -> str:
        return f"{self.prefix}-{dep.value}"

    @auto_inject
    @injectable
    def instance_auto(self, dep: Inject[Dependency]) -> str:
        return f"{self.prefix}-{dep.value}"

    @classmethod
    @auto_inject
    @injectable
    def class_auto(cls, dep: Inject[Dependency]) -> str:
        return f"{cls.__name__}-{dep.value}"

    @staticmethod
    @auto_inject
    @injectable
    def static_auto(dep: Inject[Dependency]) -> str:
        return f"static-{dep.value}"


def test_injectable_callable_supports_method_variants():
    registry = Registry()
    container = Container(registry)
    container.add(Dependency("local"))

    handler = Handler("prefix")

    assert container.call(handler.instance_call) == "prefix-local"

    with container:
        assert handler.instance_auto() == "prefix-local"
        assert Handler.class_auto() == "Handler-local"
        assert Handler.static_auto() == "static-local"

    assert container.call(Handler.class_auto) == "Handler-local"
    assert container.call(Handler.static_auto) == "static-local"
