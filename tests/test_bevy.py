from pytest import fixture, raises
from bevy.context import Context, ConflictingTypeAddedToRepository
from bevy.injectable import Injectable


@fixture()
def dep():
    class Dep(Injectable):
        ...

    return Dep


@fixture()
def dep_a(dep):
    return dep()


@fixture()
def dep_b(dep):
    return dep()


@fixture()
def app(dep):
    class App(Injectable):
        dependency: dep

    return App


# ###   TESTS   ### #


def test_context_resolution(dep_a, dep):
    c = Context().add(dep_a)
    assert c.get(dep) is dep_a


def test_context_creation(dep_a, app):
    c = Context().add(dep_a)
    a = c.create(app)
    assert a.dependency is dep_a


def test_instantiation(dep, app):
    a = app()
    assert isinstance(a.dependency, dep)


class Dependency:
    class SubDependency:
        ...


class Base(Injectable):
    dep: "Dependency"
    sub: "Dependency.SubDependency"


def test_dependency_resolution():
    d = Dependency()
    s = Dependency.SubDependency()
    c = Context().add(d).add(s)
    a = c.create(Base)
    assert a.dep is d
    assert a.sub is s


def test_propagated_creation():
    class Testing:
        ...

    parent = Context()
    child = parent.branch()
    child_instance = child.get(Testing)
    parent_instance = parent.get(Testing)
    assert child_instance is not parent_instance


def test_conflicting_types():
    class Parent:
        ...

    class Child(Parent):
        ...

    context = Context()
    context.add(Parent())

    with raises(ConflictingTypeAddedToRepository):
        context.add(Child())


def test_conflicting_same_types():
    class TestType:
        ...

    context = Context()
    context.add(TestType())

    with raises(ConflictingTypeAddedToRepository):
        context.add(TestType())


def test_conflicting_super_type():
    class Parent:
        ...

    class Child(Parent):
        ...

    context = Context()
    context.add(Child())

    with raises(ConflictingTypeAddedToRepository):
        context.add(Parent())
