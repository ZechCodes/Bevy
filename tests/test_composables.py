from unittest import TestCase
from exo.composables import Composable, uses, NotComposable
from exo.repositories import Repository


class Test(TestCase):
    def test_uses(self):
        @uses(testing=5)
        class Test:
            __dependencies__ = {}

        self.assertIn("testing", Test.__dependencies__, "Failed to add the dependency")
        self.assertEqual(
            Test.__dependencies__["testing"], 5, "Failed to add the correct dependency"
        )

    def test_not_composable(self):
        with self.assertRaises(NotComposable, msg="Failed to raise on non-composable"):

            @uses(testing=5)
            class Test:
                ...

    def test_no_repository(self):
        @uses(testing=-1)
        class Test(Composable):
            ...

        with self.assertRaises(
            TypeError, msg="Failed to raise when no repository provided"
        ):
            Test()

    def test_composable_instantiation(self):
        @uses(testing=-1)
        class Test(Composable):
            ...

        class DummyRepository(Repository):
            def get(self, *args):
                return 5

        test = Test(__repository__=DummyRepository())
        self.assertEqual(test.testing, 5, "Incorrect value was injected")

    def test_composable_create(self):
        @uses(testing=-1)
        class Test(Composable):
            ...

        class DummyRepository(Repository):
            def get(self, *args):
                return 5

        test = Test.create(DummyRepository())
        self.assertEqual(test.testing, 5, "Incorrect value was injected")
