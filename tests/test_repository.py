from unittest import TestCase
from exo.repository import Repository


class TestRepository(TestCase):
    def test_create(self):
        self.assertIsInstance(
            Repository.create(),
            Repository,
            "Repository create failed to return a repository",
        )

    def test_create_non_repo_instance(self):
        class NotARepo:
            ...

        self.assertIsInstance(
            Repository.create(NotARepo()),
            Repository,
            "Repository create failed to return a repository",
        )

    def test_create_non_repo_type(self):
        class NotARepo:
            ...

        self.assertIsInstance(
            Repository.create(NotARepo),
            Repository,
            "Repository create failed to return a repository",
        )

    def test_create_repo_instance(self):
        class Repo(Repository):
            ...

        repo = Repo()

        self.assertIs(
            Repository.create(repo),
            repo,
            "Failed to return the existing repository instance",
        )

    def test_create_repo_type(self):
        class Repo(Repository):
            ...

        self.assertIsInstance(
            Repository.create(Repo),
            Repo,
            "Failed to create an instance of the repository subclass",
        )
