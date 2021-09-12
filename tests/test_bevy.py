from bevy import Context, dependencies, Inject
from bevy.factory import Factory


def test_inject_dependencies():
    class Dep:
        ...

    @dependencies
    class Testing:
        test: Inject[Dep]

    context = Context()
    inst = context.build(Testing)

    assert isinstance(inst.test, Dep)


def test_shared_dependencies():
    class Dep:
        ...

    @dependencies
    class TestingA:
        test: Inject[Dep]

    @dependencies
    class TestingB:
        test: Inject[Dep]

    context = Context()
    instA = context.build(TestingA)
    instB = context.build(TestingB)

    assert instA.test is instB.test


def test_branching_same_dependencies():
    class Dep:
        ...

    @dependencies
    class TestingA:
        test: Inject[Dep]

    @dependencies
    class TestingB:
        test: Inject[Dep]

    context = Context()
    branch = context.branch()
    instA = context.build(TestingA)
    instB = branch.build(TestingB)

    assert instA.test is instB.test


def test_branching_different_dependencies():
    class Dep:
        ...

    @dependencies
    class TestingA:
        test: Inject[Dep]

    @dependencies
    class TestingB:
        test: Inject[Dep]

    context = Context()
    branch = context.branch()
    instB = branch.build(TestingB)
    instA = context.build(TestingA)

    assert instA.test is not instB.test


def test_branching_different_dependencies():
    class Dep:
        ...

    @dependencies
    class TestingA:
        test: Inject[Dep]

    @dependencies
    class TestingB:
        test: Inject[Dep]

    context = Context()
    branch = context.branch()
    instB = branch.build(TestingB)
    instA = context.build(TestingA)

    assert instA.test is not instB.test


def test_dependencies_matching_labels():
    class Dep:
        ...

    @dependencies
    class TestingA:
        test: Inject[Dep, "testing"]

    @dependencies
    class TestingB:
        test: Inject[Dep, "testing"]

    context = Context()
    instA = context.build(TestingA)
    instB = context.build(TestingB)

    assert instA.test is instB.test


def test_dependencies_nonmatching_labels():
    class Dep:
        ...

    @dependencies
    class TestingA:
        test: Inject[Dep, "testingA"]

    @dependencies
    class TestingB:
        test: Inject[Dep, "testingB"]

    context = Context()
    instA = context.build(TestingA)
    instB = context.build(TestingB)

    assert instA.test is instB.test


def test_factory():
    class Dep:
        ...

    @dependencies
    class Testing:
        test: Factory[Dep]

    context = Context()
    inst = context.build(Testing)

    assert isinstance(inst.test(), Dep)


def test_factory_unique():
    class Dep:
        ...

    @dependencies
    class Testing:
        test: Factory[Dep]

    context = Context()
    inst = context.build(Testing)

    assert inst.test() is not inst.test()
