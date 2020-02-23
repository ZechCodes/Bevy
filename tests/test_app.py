from unittest import TestCase
from exo.exo import Exo
from exo.app import App, AppResult
import asyncio


class TestExoApp(TestCase):
    def test_run(self):
        class Dependency(Exo):
            def __init__(self):
                self.message = "interface"

        class DependencyB(Dependency):
            def __init__(self, message):
                self.message = message

        class Component(Exo):
            dep: Dependency
            result: AppResult

            def __init__(self):
                self.result.result = self.dep.message

        class TestApp(App):
            def __init__(self, components):
                self.add_component_dependency(DependencyB("subclass"))

        app = TestApp([Component])
        result = app.run()

        self.assertEqual(
            "subclass",
            result.result,
            "The result returned was incorrect. Component dependency likely failed.",
        )
