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
