from pytest import fixture
from bevy.context import Context
from bevy.bevy import Bevy


@fixture()
def dep():
    class Dep(Bevy):
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
    class App(Bevy):
        dependency: dep
    return App


# ###   TESTS   ### #


def test_context_resolution(dep_a, dep):
    c = Context().load(dep_a)
    assert c.get(dep) is dep_a


def test_context_creation(dep_a, app):
    c = Context().load(dep_a)
    a = c.create(app)
    assert a.dependency is dep_a


def test_instantiation(dep, app):
    a = app()
    assert isinstance(a.dependency, dep)


def test_dependency_resolution():
    class Dependency:
        ...

    class Base:
        dep: "Dependency"

    d = Dependency()
    c = Context().load(d)
    a = c.create(Base)
    assert a.dep is d
