from bevy import AutoInject, Context, Inject
from bevy.builder import Builder


class Dep:
    ...


def test_dependency_detection():
    class Testing(AutoInject, auto_detect=True):
        test: Dep

    inst = Testing()
    assert isinstance(inst.test, Dep)


def test_independent_dependencies():
    class Testing(AutoInject, auto_detect=True):
        test: Dep

    inst_a = Testing()
    inst_b = Testing()
    assert inst_a.test is not inst_b.test


def test_shared_dependencies():
    class Testing(AutoInject, auto_detect=True):
        test: Dep

    context = Context()
    builder = context.bind(Testing)
    inst_a = builder()
    inst_b = builder()

    assert inst_a.test is inst_b.test


def test_manual_inject():
    class Testing(AutoInject, auto_detect=True):
        test = Inject(Dep)

    inst = Testing()
    assert isinstance(inst.test, Dep)


def test_builder():
    class Testing(AutoInject, auto_detect=True):
        builder: Builder[Dep]

    inst = Testing()
    assert isinstance(inst.builder(), Dep)
    assert inst.builder() is not inst.builder()
