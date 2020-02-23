from pytest import fixture
from exo.exo import Exo, ExoBuilder


class TestBuilder:
    @fixture
    def dependency(self):
        class Dep(Exo):
            ...

        return Dep

    @fixture
    def sub_dependency(self, dependency):
        class SubDep(dependency):
            ...

        return SubDep

    @fixture
    def app(self, dependency):
        class App(Exo):
            dep: dependency

        return App

    def test_declare(self, app, sub_dependency):
        a = app.declare(sub_dependency()).build()

        assert isinstance(a.dep, sub_dependency)

    def test_imperative_dependencies(self, app, dependency):
        builder = ExoBuilder(app)
        builder.dependencies(imp=dependency)
        a = builder.build()

        assert hasattr(a, "imp")

    def test_exo_constructor_ret_type(self, app, dependency):
        assert isinstance(app(), app)

    def test_exo_constructor_ret_dependencies(self, app, dependency):
        assert isinstance(app().dep, dependency)
