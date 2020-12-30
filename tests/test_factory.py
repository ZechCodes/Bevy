from pytest import fixture
from bevy import Bevy, Context, Factory


@fixture
def dependency(sub_dependency):
    class Dep(Bevy):
        sub: sub_dependency

    return Dep


@fixture
def sub_dependency():
    class SubDep:
        ...

    return SubDep


@fixture
def app(dependency):
    class App(Bevy):
        dep_factory: Factory[dependency]

        def get(self) -> dependency:
            return self.dep_factory()

    return App


# ###   TESTS   ### #


def test_factory(app, dependency):
    a = app()

    assert isinstance(a.get(), dependency)


def test_distinct_instances(app, dependency):
    a = app()

    assert a.get() is not a.get()


def test_deps_inherited(app, dependency, sub_dependency):
    s = sub_dependency()
    c = Context().add(s)
    a = c.get(app)

    x = a.get().sub
    assert x is s


def test_same_deps(app, dependency, sub_dependency):
    a = app()

    x = a.get().sub
    y = a.get().sub
    assert x is y
