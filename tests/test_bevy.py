from pytest import fixture
from bevy.bevy import Bevy, BevyBuilder


class TestBuilder:
    @fixture
    def dependency(self):
        class Dep(Bevy):
            ...

        return Dep

    @fixture
    def sub_dependency(self, dependency):
        class SubDep(dependency):
            ...

        return SubDep

    @fixture
    def app(self, dependency):
        class App(Bevy):
            dep: dependency

        return App

    def test_declare(self, app, sub_dependency):
        a = app.declare(sub_dependency()).build()

        assert isinstance(a.dep, sub_dependency)

    def test_imperative_dependencies(self, app, dependency):
        builder = BevyBuilder(app)
        builder.dependencies(imp=dependency)
        a = builder.build()

        assert hasattr(a, "imp")

    def test_bevy_constructor_ret_type(self, app, dependency):
        assert isinstance(app(), app)

    def test_bevy_constructor_ret_dependencies(self, app, dependency):
        assert isinstance(app().dep, dependency)
