from bevy import Context, injectable, is_injectable
from bevy.factory import Factory
from bevy.label import Label


class Dependency:
    def __init__(self, name):
        self.name = name


class DependencyB:
    def __init__(self, name):
        self.name = f"__{name}__"


@injectable
class BranchDep:
    dep: Dependency


@injectable
class App:
    dep: Dependency


def test_simple_construction():
    @injectable
    class Testing:
        def __init__(self):
            ...

    Testing()


def test_for_double_init():
    @injectable
    class Testing:
        msg = "only once"

        def __init__(self):
            assert Testing.msg == "only once"
            Testing.msg = "called twice"

    Testing()


def test_construct():
    context = Context(App)
    context.add(Dependency("foobar"))
    app = context.build()

    assert app.dep.name == "foobar"


def test_branching_inheritance():
    @injectable
    class App:
        dep: BranchDep

    context = Context(App)
    context.add(Dependency("foobar"))
    context.branch(BranchDep)
    app = context.build()

    assert app.dep.dep.name == "foobar"


def test_branching_propagation():
    context = Context(App)
    context.add(Dependency("foobar"))
    branch = context.branch(BranchDep)
    branch.add(Dependency("hello world"))
    app = context.build()

    assert context.get(BranchDep).dep.name == "hello world"
    assert app.dep.name == "foobar"


def test_add_as():
    context = Context(App)
    context.add_as(DependencyB("foobar"), Dependency)
    app = context.build()

    assert app.dep.name == "__foobar__"


def test_factories():
    class Dep:
        def __init__(self, name):
            self.name = f"__{name}__"

    @injectable
    class App:
        factory: Factory[Dep]

    app = Context(App).build()
    assert app.factory("foobar").name == "__foobar__"


def test_injectable():
    assert is_injectable(App)


def test_no_context():
    class Dep:
        ...

    @injectable
    class App:
        dep: Dep

    assert App().dep


def test_label():
    class Dep:
        def __init__(self, value="default"):
            self.value = value

    @injectable
    class App:
        dep: Label[Dep:"dep"]

    app = Context(App).build()
    assert isinstance(app.dep, Dep)


def test_label_same_instance():
    class Dep:
        def __init__(self, value="default"):
            self.value = value

    @injectable
    class AppA:
        dep: Label[Dep:"dep"]

    @injectable
    class AppB:
        dep: Label[Dep:"dep"]

    builder = Context(AppA)
    app_b = builder.get(AppB)
    app_a = builder.build()
    assert app_a.dep is app_b.dep


def test_label_different_instances():
    class Dep:
        def __init__(self, value="default"):
            self.value = value

    @injectable
    class AppA:
        dep: Label[Dep:"dep_a"]

    @injectable
    class AppB:
        dep: Label[Dep:"dep_b"]

    builder = Context(AppA)
    app_b = builder.get(AppB)
    app_a = builder.build()
    assert app_a.dep is not app_b.dep


def test_label_injection():
    class Dep:
        def __init__(self, value="default"):
            self.value = value

    @injectable
    class App:
        dep: Label[Dep:"dep"]

    builder = Context(App)
    builder.add(Label(Dep("dep"), "dep"))
    app = builder.build()
    assert app.dep.value == "dep"
