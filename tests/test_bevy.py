from pytest import fixture
from bevy.context import Context
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
