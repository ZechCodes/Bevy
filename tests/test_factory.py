from pytest import fixture
from bevy import Bevy, Factory


class TestBuilder:
    @fixture
    def dependency(self, sub_dependency):
        class Dep(Bevy):
            sub: sub_dependency

        return Dep

    @fixture
    def sub_dependency(self):
        class SubDep:
            ...

        return SubDep

    @fixture
    def app(self, dependency):
        class App(Bevy):
            dep_factory: Factory[dependency]

            def get(self) -> dependency:
                return self.dep_factory()

        return App

    def test_factory(self, app, dependency):
        a = app()

        assert isinstance(a.get(), dependency)

    def test_distinct_instances(self, app, dependency):
        a = app()

        assert a.get() is not a.get()

    def test_deps_inherited(self, app, dependency, sub_dependency):
        s = sub_dependency()
        a = app.context(s).build()

        x = a.get().sub
        assert x is s

    def test_same_deps(self, app, dependency, sub_dependency):
        a = app()

        x = a.get().sub
        y = a.get().sub
        assert x is y
