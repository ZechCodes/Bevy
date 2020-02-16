from unittest import TestCase
from exo.exo import Exo


class TestExeDependencies(TestCase):
    def test_dependencies(self):
        class Dep(Exo):
            ...

        class App(Exo):
            dep: Dep

        self.assertEqual(
            App.__dependencies__, {"dep": Dep}, "Dependencies failed to set correctly"
        )

    def test_dependency_injection(self):
        class Dep(Exo):
            ...

        class App(Exo):
            dep: Dep

        app = App()
        self.assertTrue(
            hasattr(app, "dep"), "Failed to inject the dependency with the correct name"
        )
        self.assertIsInstance(app.dep, Dep, "Dependency is of the wrong type")

    def test_dependency_injection_sharing(self):
        class Dep(Exo):
            ...

        class App(Exo):
            dep: Dep

        class App2(Exo):
            dep: Dep

        app = App()
        app2 = App2(__repository__=app.__repository__)
        self.assertIs(app.dep, app2.dep, "Dependency was not shared")
