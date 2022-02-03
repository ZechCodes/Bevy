from bevy import AutoInject, Context, Inject, detect_dependencies
from bevy.builder import Builder


class Dep:
    ...


def test_dependency_detection():
    @detect_dependencies
    class Testing(AutoInject):
        test: Dep

    inst = Testing()
    assert isinstance(inst.test, Dep)


def test_independent_dependencies():
    @detect_dependencies
    class Testing(AutoInject):
        test: Dep

    inst_a = Testing()
    inst_b = Testing()
    assert inst_a.test is not inst_b.test


def test_shared_dependencies():
    @detect_dependencies
    class Testing(AutoInject):
        test: Dep

    context = Context()
    builder = context.bind(Testing)
    inst_a = builder()
    inst_b = builder()

    assert inst_a.test is inst_b.test


def test_manual_inject():
    @detect_dependencies
    class Testing(AutoInject):
        test = Inject(Dep)

    inst = Testing()
    assert isinstance(inst.test, Dep)


def test_builder():
    @detect_dependencies
    class Testing(AutoInject):
        builder: Builder[Dep]

    inst = Testing()
    assert isinstance(inst.builder(), Dep)
    assert inst.builder() is not inst.builder()


def test_single_context_instance():
    @detect_dependencies
    class Testing(AutoInject):
        test: Dep

    inst = Testing()
    assert inst.__bevy_context__ is inst.__bevy_context__


def test_multiple_contexts():
    @detect_dependencies
    class Testing(AutoInject):
        test: Dep

    inst_a = Testing()
    inst_b = Testing()
    assert inst_a.__bevy_context__ is not inst_b.__bevy_context__


def test_slots():
    @detect_dependencies
    class Testing(AutoInject):
        __slots__ = []
        test: Dep

    inst = Testing()
    assert isinstance(inst.test, Dep)


def test_non_branching():
    @detect_dependencies
    class Child(AutoInject):
        test: Dep

    @detect_dependencies
    class Testing(AutoInject):
        test: Dep
        child: Child

    parent = Testing()
    assert parent.test is parent.child.test


def test_branching():
    @detect_dependencies
    class Child(AutoInject):
        test: Dep

    @detect_dependencies
    class Testing(AutoInject):
        test: Dep
        child: Child

    context = Context()
    child_context = context.branch()
    parent = context.bind(Testing)()
    child = child_context.bind(Child)()
    child_context.add(Dep())
    context.add(child)

    assert parent.child is child
    assert parent.test is not parent.child.test


def test_branching_inheritance():
    @detect_dependencies
    class Child(AutoInject):
        test: Dep

    @detect_dependencies
    class Testing(AutoInject):
        test: Dep
        child: Child

    context = Context()
    child_context = context.branch()
    parent = context.bind(Testing)()
    context.add(Dep())
    child = child_context.bind(Child)()
    context.add(child)

    assert parent.child is child
    assert parent.test is parent.child.test
