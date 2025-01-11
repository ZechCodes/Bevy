from tramp.optionals import Optional

from bevy import dependency, inject, Registry
from bevy.hooks import Hook, hooks
from bevy.ext import type_factory


class DummyObject:
    def __init__(self, value=None):
        self.value = value


def test_containers():
    registry = Registry()
    registry.add_factory(lambda _: DummyObject(), DummyObject)
    container = registry.create_container()

    instance = container.get(DummyObject)
    assert isinstance(instance, DummyObject)
    assert container.get(DummyObject) is instance


def test_inherit_from_parent_container():
    registry = Registry()
    registry.add_factory(lambda _: DummyObject(), DummyObject)

    parent = registry.create_container()
    child = parent.branch()

    instance = parent.get(DummyObject)
    assert child.get(DummyObject) is instance


def test_child_overrides_parent_container():
    registry = Registry()
    registry.add_factory(lambda _: DummyObject(), DummyObject)

    parent = registry.create_container()
    child = parent.branch()

    child_instance = child.get(DummyObject)
    parent_instance = parent.get(DummyObject)
    assert child_instance is not parent_instance
    assert child_instance is child.get(DummyObject)
    assert parent_instance is parent.get(DummyObject)


def test_injection():
    def test(d: DummyObject = dependency()):
        assert isinstance(d, DummyObject)

    registry = Registry()
    registry.add_factory(lambda _: DummyObject(), DummyObject)
    container = registry.create_container()
    container.call(test)


def test_injection_wrapper():
    @inject
    def test(d: DummyObject = dependency()):
        assert isinstance(d, DummyObject)

    with Registry() as registry:
        registry.add_factory(lambda _: DummyObject(), DummyObject)

        test()


def test_injection_factories():
    @inject
    def test(d: DummyObject = dependency(lambda _: DummyObject("a"))):
        assert isinstance(d, DummyObject) and d.value == "a"

    with Registry() as registry:
        test()


def test_get_instance_hook():
    values = ["a", "b"]
    index = 0
    def hook(_, dependency_type):
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
    def hook(_, dependency_type):
        nonlocal index
        if dependency_type is DummyObject:
            old_index, index = index, index + 1
            return Optional.Some(DummyObject(values[old_index]))

        return Optional.Nothing()

    registry = Registry()
    registry.add_hook(Hook.CREATE_INSTANCE, hook)
    container = registry.create_container()

    assert container.get(DummyObject).value == values[0]
    assert container.get(DummyObject).value == values[0]


def test_created_instance_hook():
    runs = 0
    def hook(_, value):
        nonlocal runs
        if isinstance(value, DummyObject):
            runs += 1

    registry = Registry()
    registry.add_factory(lambda _: DummyObject(), DummyObject)
    registry.add_hook(Hook.CREATED_INSTANCE, hook)

    container = registry.create_container()
    container.get(DummyObject)
    container.get(DummyObject)

    assert runs == 1


def test_got_instance_hook():
    runs = 0
    def hook(_, value):
        nonlocal runs
        if isinstance(value, DummyObject):
            runs += 1

    registry = Registry()
    registry.add_factory(lambda _: DummyObject(), DummyObject)
    registry.add_hook(Hook.GOT_INSTANCE, hook)

    container = registry.create_container()
    container.get(DummyObject)
    container.get(DummyObject)

    assert runs == 2


def test_unsupported_dependency_hook():
    @hooks.HANDLE_UNSUPPORTED_DEPENDENCY
    def hook(_, dependency_type):
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