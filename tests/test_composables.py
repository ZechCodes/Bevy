from unittest import TestCase
from exo.composables import Composable, uses, NotComposable
from exo.repositories import Repository


class TestComposables(TestCase):
    def test_uses(self):
        @uses(testing=5)
        class Test:
            __dependencies__ = {}

        self.assertIn("testing", Test.__dependencies__, "Failed to add the dependency")
        self.assertEqual(
            Test.__dependencies__["testing"], 5, "Failed to add the correct dependency"
        )

    def test_uses_direct(self):
        class Test:
            __dependencies__ = {}

        uses(Test, testing=5)

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
        sentinel = object()

        @uses(testing="test")
        class Test(Composable):
            ...

        repo = Repository()
        repo.set("test", sentinel, instantiate=False)

        test = Test(__repository__=repo)

        self.assertIs(test.testing, sentinel, "Incorrect value was injected")

    def test_composable_create(self):
        sentinel = object()

        @uses(testing="test")
        class Test(Composable):
            ...

        repo = Repository()
        repo.set("test", sentinel, instantiate=False)

        test = Test.create(repo)
        self.assertIs(test.testing, sentinel, "Incorrect value was injected")
