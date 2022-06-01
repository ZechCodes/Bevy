from bevy import BevyInject, Context, Inject, Detection
from pytest import raises


class Dependency:
    def __init__(self, value=-1):
        self.value = value


def test_dependency_creation():
    class Test(BevyInject):
        dep: Dependency = Inject()

    test = Test()
    assert isinstance(test.dep, Dependency)


def test_dependency_detection():
    class Test(BevyInject, bevy=Detection.ALL):
        dep: Dependency

    test = Test()
    assert isinstance(test.dep, Dependency)


def test_dependency_only_detection():
    class Test(BevyInject, bevy=Detection.ONLY["dep"]):
        dep: Dependency
        no_dep: Dependency

    test = Test()
    assert isinstance(test.dep, Dependency)
    assert not hasattr(test, "no_dep")


def test_dependency_ignore_detection():
    class Test(BevyInject, bevy=Detection.IGNORE["no_dep"]):
        dep: Dependency
        no_dep: Dependency

    test = Test()
    assert isinstance(test.dep, Dependency)
    assert not hasattr(test, "no_dep")


def test_shared_dependencies():
    class TestA(BevyInject, bevy=Detection.ALL):
        dep: Dependency

    class TestB(BevyInject, bevy=Detection.ALL):
        dep: Dependency

    context = Context()
    a = context.create(TestA)
    b = context.create(TestB)
    assert isinstance(a.dep, Dependency)
    assert isinstance(b.dep, Dependency)
    assert a.dep is b.dep


def test_inherited_dependencies():
    class Test(BevyInject, bevy=Detection.ALL):
        dep: Dependency

    parent = Context()
    parent.create(Dependency, add_to_context=True)
    child = parent.branch()
    test = child.create(Test)
    assert test.dep is parent.get(Dependency)
