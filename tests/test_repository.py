from unittest import TestCase
from pytest import fixture
from bevy.repository import Repository, BevyRepositoryMustBeMatchingTypes, Strategy
from bevy.bevy import Bevy
import random


class TestRepository(TestCase):
    def test_create_scope(self):
        repo = Repository()
        child = repo.create_scope()

        self.assertIsNot(child, repo, "Failed to create child repo")

    def test_create_scope_parent(self):
        repo = Repository()
        child = repo.create_scope()

        self.assertIs(child._parent, repo, "Failed to assign parent of child repo")

    def test_create_scope_type(self):
        class CustomRepo(Repository):
            ...

        repo = CustomRepo()
        child = repo.create_scope()

        self.assertIsInstance(
            child, CustomRepo, "Failed to create child repo of parent's type"
        )

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

    # TEST GET/HAS/SET
    def test_set_instance(self):
        repo = Repository()
        sentinel = object()

        self.assertEqual(
            repo.set(object, sentinel),
            sentinel,
            "Failed to set the value in the repository",
        )

    def test_set_type(self):
        repo = Repository()

        self.assertEqual(
            repo.set(str, str),
            "",
            "Failed to instantiate and set the value in the repository",
        )

    def test_set_unmatched(self):
        repo = Repository()

        with self.assertRaises(
            BevyRepositoryMustBeMatchingTypes, msg="Failed to detect unmatched types"
        ):
            repo.set(str, 1)

    def test_not_has(self):
        repo = Repository()

        self.assertFalse(
            repo.has(str), "Has check found something when it shouldn't have"
        )

    def test_has(self):
        repo = Repository()
        repo.set(str, "")

        self.assertTrue(repo.has(str), "Failed to find existing instance")

    def test_has_propagate(self):
        repo = Repository()
        repo.set(str, "")
        child = Repository(repo)

        self.assertTrue(child.has(str), "Failed to find existing instance on parent")

    def test_has_no_propagate(self):
        repo = Repository()
        repo.set(str, "")
        child = Repository(repo)

        self.assertFalse(
            child.has(str, propagate=False), "Propagated to parent when disabled"
        )

    def test_get_existing(self):
        repo = Repository()
        repo.set(str, "")

        self.assertEqual(repo.get(str), "", "Failed to find existing instance")

    def test_get_instantiate(self):
        repo = Repository()

        self.assertEqual(repo.get(str), "", "Failed to create instance")

    def test_get_default(self):
        repo = Repository()

        self.assertEqual(
            repo.get(str, default="NOVAL"), "NOVAL", "Failed to create instance"
        )

    def test_get_propagate(self):
        repo = Repository()
        repo.set(str, "")
        child = Repository(repo)

        self.assertEqual(
            child.get(str), "", "Failed to find existing instance on parent"
        )

    def test_get_no_propagate(self):
        repo = Repository()
        repo.set(str, "")
        child = Repository(repo)

        self.assertEqual(
            child.get(str, default="NOVAL", propagate=False),
            "NOVAL",
            "Propagated to parent when disabled",
        )

    def test_get_propagate_default(self):
        repo = Repository()
        child = Repository(repo)

        self.assertEqual(
            child.get(str, default="NOVAL"),
            "NOVAL",
            "Failed to propagate default value",
        )

    def test_get_propagate_override(self):
        repo = Repository()
        repo.set(str, "")
        child = Repository(repo)
        child.set(str, "child")

        self.assertEqual(child.get(str), "child", "Failed to find value on child repo")

    def test_get_subclass(self):
        class ValueParent:
            ...

        class ValueChild(ValueParent):
            ...

        repo = Repository()
        repo.set(ValueChild, ValueChild)

        self.assertIsInstance(
            repo.get(ValueParent),
            ValueChild,
            "Failed to match a sub class of the look up type",
        )

    def test_no_inherit(self):
        class Extension:
            __repository_strategy__ = Strategy.NO_INHERIT

        parent = Repository()
        child = parent.create_scope()

        self.assertIsNot(
            parent.get(Extension),
            child.get(Extension),
            "Inherited when it was not supposed to",
        )

    def test_always_create(self):
        class Extension:
            __repository_strategy__ = Strategy.ALWAYS_CREATE

        repo = Repository()

        self.assertIsNot(
            repo.get(Extension),
            repo.get(Extension),
            "Failed to create for each request",
        )

    def test_always_create_inherit(self):
        class Extension:
            __repository_strategy__ = Strategy.ALWAYS_CREATE

        parent = Repository()
        child = parent.create_scope()

        self.assertIsNot(
            parent.get(Extension),
            child.get(Extension),
            "Inherited an ALWAYS_CREATE instance",
        )

    def test_repository_access(self):
        class App(Bevy):
            context: Repository

        repo = Repository()
        self.assertIs(repo.get(App).context, repo)


class TestRepositoryInherited:
    @fixture
    def dependency(self):
        class Dependency:
            def __init__(self, name, rand=True):
                self._name = name
                self._rand = random.randint(0, 100) if rand else ""

            @property
            def name(self):
                return f"{self._name}{self._rand}"

        return Dependency

    @fixture
    def child_bevy(self, dependency):
        class Child(Bevy):
            dep: dependency

        return Child

    @fixture
    def owner(self, child_bevy, dependency):
        class Owner(Bevy):
            dep: dependency
            child: child_bevy

        return Owner

    def test_inherited(self, owner, dependency):
        app = owner.declare(dependency("foo", False)).build()
        assert app.dep.name == "foo"

    def test_match(self, owner, dependency):
        app = owner.declare(dependency("foo")).build()
        assert app.dep.name == app.child.dep.name
