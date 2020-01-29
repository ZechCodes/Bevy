from unittest import TestCase
from exo.repositories import (
    NullRepository,
    Repository,
    RepositoryNameDoesntExist,
    RepositoryNameExists,
)


class TestNullRepository(TestCase):
    def test_is_null(self):
        repo = NullRepository()

        self.assertTrue(repo.is_null(), "Null Repository is not null")

    def test_not_null(self):
        repo = Repository()

        self.assertFalse(repo.is_null(), "Repository is null")


class TestRepository(TestCase):
    def test_parent(self):
        parent_repo = Repository()
        repo = parent_repo.create_child()

        self.assertIs(parent_repo, repo.parent, "The parent is not set correctly")

    def test_parent_null(self):
        repo = Repository()

        self.assertIs(repo.parent, NullRepository(), "The parent must be null")

    def test_get(self):
        class Test:
            pass

        repo = Repository()
        inst = repo.get(Test)

        self.assertIsInstance(
            inst, Test, "Repository didn't not return an instance of the correct type"
        )

    def test_get_single_instance(self):
        class Test:
            pass

        repo = Repository()
        inst = repo.get(Test)
        inst2 = repo.get(Test)

        self.assertIs(inst, inst2, "Repository instantiated multiple instances")

    def test_get_inheritance(self):
        class Test:
            pass

        repo = Repository()
        child_repo = repo.create_child()

        inst = repo.get(Test)
        inst2 = child_repo.get(Test)

        self.assertIs(inst, inst2, "Repository inheritance failed")

    def test_get_reverse_inheritance(self):
        class Test:
            pass

        repo = Repository()
        child_repo = repo.create_child()

        inst = child_repo.get(Test)
        inst2 = repo.get(Test)

        self.assertIsNot(inst, inst2, "Repository inheritance failed")

    def test_repository_ignore(self):
        class Test:
            __repository_ignore__ = True

        repo = Repository()

        inst1 = repo.get(Test)
        inst2 = repo.get(Test)

        self.assertIsNot(inst1, inst2, "Repository instantiated multiple times")

    def test_repository_build(self):
        sentinel = object()

        class Test:
            @classmethod
            def __repository_build__(cls):
                return sentinel

        repo = Repository()
        number = repo.get(Test)

        self.assertIs(
            number, sentinel, "Repository failed to correctly call build method"
        )

    def test_repository_set(self):
        sentinel = object()

        class Test:
            @classmethod
            def __repository_build__(cls):
                return sentinel

        repo = Repository()
        repo.set("testing", Test)

        self.assertIs(
            repo.get("testing"),
            sentinel,
            "Repository failed to load the corrected named instance",
        )

    def test_repository_set_extra(self):
        repo = Repository()
        repo.set("testing", object)

        with self.assertRaises(
            RepositoryNameExists, msg="Failed to raise name exists exception"
        ):
            repo.set("testing", object)

    def test_repository_get_nonexistent_name(self):
        repo = Repository()

        with self.assertRaises(
            RepositoryNameDoesntExist,
            msg="Failed to raise name doesn't exist exception",
        ):
            repo.get("testing")
