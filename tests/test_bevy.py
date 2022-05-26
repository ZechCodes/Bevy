from bevy import Context, Inject, Dependencies
from bevy.function_provider import FunctionProvider
from pytest import raises


class Dependency:
    def __init__(self, value=-1):
        self.value = value


def test_dependency_creation():
    context = Context()
    assert isinstance(context.get_provider_for(Dependency).get_instance(), Dependency)


def test_injection():
    class TestClass(Dependencies):
        dependency: Inject[Dependency]

    context = Context()
    dep_provider = context.get_provider_for(Dependency)
    test_provider = context.get_provider_for(TestClass)
    assert dep_provider.get_instance() is test_provider.get_instance().dependency


def test_injection_from_context():
    class TestClass(Dependencies):
        dependency: Inject[Dependency]

    context = Context()
    dep = context.get(Dependency)
    test = context.get(TestClass)
    assert dep is test.dependency


def test_context_has():
    class Dep2:
        ...

    context = Context()
    context.get(Dependency)
    assert context.has(Dependency)
    assert not context.has(Dep2)


def test_context_add_as_type():
    class Dep2:
        ...

    context = Context()
    context.add(Dep2(), as_type=Dependency)
    assert isinstance(context.get(Dependency), Dep2)


def test_context_add_instance():
    context = Context()
    context.add(Dependency(10))
    assert context.get(Dependency).value == 10


def test_inheritance():
    class TestClass(Dependencies):
        dependency: Inject[Dependency]

    context = Context()
    branch_context = context.branch()
    context_provider = context.get_provider_for(Dependency)
    branch_provider = branch_context.get_provider_for(Dependency)
    assert context_provider.get_instance() is branch_provider.get_instance()


def test_function_providers():
    def function(dep: Dependency = Inject) -> int:
        return dep.value

    context = Context()
    context.add(Dependency(10))
    func = context.bind(function)

    assert func() == 10


def test_getting_a_function():
    def function(dep: Dependency = Inject) -> int:
        return dep.value

    context = Context()
    context.add(Dependency(10))
    context.add_provider(FunctionProvider(function))

    assert context.get(function, provider_type=FunctionProvider)() == 10


def test_getting_a_function_with_matching_signature():
    def dep_function(dep: Dependency = Inject) -> int:
        return dep.value + 10

    def function(dep: Dependency = Inject) -> int:
        return dep.value

    context = Context()
    context.add(Dependency(10))
    context.add_provider(FunctionProvider(dep_function))

    assert context.get(function, provider_type=FunctionProvider)() == 20


def test_auto_context_creation():
    class TestDep(Dependencies):
        dep: Inject[Dependency]

    class Test(Dependencies):
        dep_a: Inject[Dependency]
        dep_b: Inject[TestDep]

    test = Test()
    assert test.dep_a is test.dep_b.dep


def test_deferred_bevy_setup():
    class Test(Dependencies):
        dep: "Inject[Dep]"

    # Need to hoist the dependency into the global namespace so that it can be found by inspect.get_annotations
    global Dep

    class Dep:
        ...

    # If this ever fails to raise the AttributeError, then we can likely remove the deferred injector builder.
    with raises(AttributeError):
        assert not isinstance(Test.dep, Inject)

    context = Context()
    test = context.get(Test)
    assert isinstance(test.dep, Dep)


def test_bevy_setup():
    class Test(Dependencies):
        dep_a: Inject[Dependency]
        dep_b: "Inject[Dependency]"

    assert isinstance(Test.dep_a, Inject)
    assert isinstance(Test.dep_b, Inject)


def test_inherited_dependencies():
    class TestParent(Dependencies):
        dep: Inject[Dependency]

    class TestChild(TestParent):
        ...

    context = Context()
    parent = context.get(TestParent)
    inst = context.get(TestChild)
    assert isinstance(parent.dep, Dependency)
    assert isinstance(inst.dep, Dependency)
    assert inst.dep is parent.dep
