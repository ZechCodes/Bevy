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
