from unittest import TestCase
from pytest import fixture
from bevy.context import Context, BevyContextMustBeMatchingTypes, Strategy
from bevy.bevy import Bevy
import random


class TestContext(TestCase):
    def test_create_scope(self):
        context = Context()
        child = context.create_scope()

        self.assertIsNot(child, context, "Failed to create child context")

    def test_create_scope_parent(self):
        context = Context()
        child = context.create_scope()

        self.assertIs(
            child._parent, context, "Failed to assign parent of child context"
        )

    def test_create_scope_type(self):
        class CustomRepo(Context):
            ...

        context = CustomRepo()
        child = context.create_scope()

        self.assertIsInstance(
            child, CustomRepo, "Failed to create child context of parent's type"
        )

    def test_create(self):
        self.assertIsInstance(
            Context.create(), Context, "Context create failed to return a context"
        )

    def test_create_non_context_instance(self):
        class NotARepo:
            ...

        self.assertIsInstance(
            Context.create(NotARepo()),
            Context,
            "Context create failed to return a context",
        )

    def test_create_non_context_type(self):
        class NotARepo:
            ...

        self.assertIsInstance(
            Context.create(NotARepo),
            Context,
            "Context create failed to return a context",
        )

    def test_create_context_instance(self):
        class Repo(Context):
            ...

        context = Repo()

        self.assertIs(
            Context.create(context),
            context,
            "Failed to return the existing context instance",
        )

    def test_create_context_type(self):
        class Repo(Context):
            ...

        self.assertIsInstance(
            Context.create(Repo),
            Repo,
            "Failed to create an instance of the context subclass",
        )

    # TEST GET/HAS/SET
    def test_set_instance(self):
        context = Context()
        sentinel = object()

        self.assertEqual(
            context.set(object, sentinel),
            sentinel,
            "Failed to set the value in the context",
        )

    def test_set_type(self):
        context = Context()

        self.assertEqual(
            context.set(str, str),
            "",
            "Failed to instantiate and set the value in the context",
        )

    def test_set_unmatched(self):
        context = Context()

        with self.assertRaises(
            BevyContextMustBeMatchingTypes, msg="Failed to detect unmatched types"
        ):
            context.set(str, 1)

    def test_not_has(self):
        context = Context()

        self.assertFalse(
            context.has(str), "Has check found something when it shouldn't have"
        )

    def test_has(self):
        context = Context()
        context.set(str, "")

        self.assertTrue(context.has(str), "Failed to find existing instance")

    def test_has_propagate(self):
        context = Context()
        context.set(str, "")
        child = Context(context)

        self.assertTrue(child.has(str), "Failed to find existing instance on parent")

    def test_has_no_propagate(self):
        context = Context()
        context.set(str, "")
        child = Context(context)

        self.assertFalse(
            child.has(str, propagate=False), "Propagated to parent when disabled"
        )

    def test_get_existing(self):
        context = Context()
        context.set(str, "")

        self.assertEqual(context.get(str), "", "Failed to find existing instance")

    def test_get_instantiate(self):
        context = Context()

        self.assertEqual(context.get(str), "", "Failed to create instance")

    def test_get_default(self):
        context = Context()

        self.assertEqual(
            context.get(str, default="NOVAL"), "NOVAL", "Failed to create instance"
        )

    def test_get_propagate(self):
        context = Context()
        context.set(str, "")
        child = Context(context)

        self.assertEqual(
            child.get(str), "", "Failed to find existing instance on parent"
        )

    def test_get_no_propagate(self):
        context = Context()
        context.set(str, "")
        child = Context(context)

        self.assertEqual(
            child.get(str, default="NOVAL", propagate=False),
            "NOVAL",
            "Propagated to parent when disabled",
        )

    def test_get_propagate_default(self):
        context = Context()
        child = Context(context)

        self.assertEqual(
            child.get(str, default="NOVAL"),
            "NOVAL",
            "Failed to propagate default value",
        )

    def test_get_propagate_override(self):
        context = Context()
        context.set(str, "")
        child = Context(context)
        child.set(str, "child")

        self.assertEqual(
            child.get(str), "child", "Failed to find value on child context"
        )

    def test_get_subclass(self):
        class ValueParent:
            ...

        class ValueChild(ValueParent):
            ...

        context = Context()
        context.set(ValueChild, ValueChild)

        self.assertIsInstance(
            context.get(ValueParent),
            ValueChild,
            "Failed to match a sub class of the look up type",
        )

    def test_no_inherit(self):
        class Extension:
            __context_strategy__ = Strategy.NO_INHERIT

        parent = Context()
        child = parent.create_scope()

        self.assertIsNot(
            parent.get(Extension),
            child.get(Extension),
            "Inherited when it was not supposed to",
        )

    def test_always_create(self):
        class Extension:
            __context_strategy__ = Strategy.ALWAYS_CREATE

        context = Context()

        self.assertIsNot(
            context.get(Extension),
            context.get(Extension),
            "Failed to create for each request",
        )

    def test_always_create_inherit(self):
        class Extension:
            __context_strategy__ = Strategy.ALWAYS_CREATE

        parent = Context()
        child = parent.create_scope()

        self.assertIsNot(
            parent.get(Extension),
            child.get(Extension),
            "Inherited an ALWAYS_CREATE instance",
        )

    def test_context_access(self):
        class App(Bevy):
            context: Context

        context = Context()
        self.assertIs(context.get(App).context, context)


class TestContextInherited:
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
        app = owner.context(dependency("foo", False)).build()
        assert app.dep.name == "foo"

    def test_match(self, owner, dependency):
        app = owner.context(dependency("foo")).build()
        assert app.dep.name == app.child.dep.name
