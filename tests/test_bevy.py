from bevy import Constructor, Factory, Injectable


class Dependency:
    def __init__(self, name):
        self.name = name


class DependencyB:
    def __init__(self, name):
        self.name = f"__{name}__"


class BranchDep(Injectable):
    dep: Dependency


class App(Injectable):
    dep: Dependency


def test_construct():
    constructor = Constructor(App)
    constructor.add(Dependency("foobar"))
    app = constructor.build()

    assert app.dep.name == "foobar"


def test_branching_inheritance():
    class App(Injectable):
        dep: BranchDep

    constructor = Constructor(App)
    constructor.add(Dependency("foobar"))
    constructor.branch(BranchDep)
    app = constructor.build()

    assert app.dep.dep.name == "foobar"


def test_branching_propagation():
    constructor = Constructor(App)
    constructor.add(Dependency("foobar"))
    branch = constructor.branch(BranchDep)
    branch.add(Dependency("hello world"))
    app = constructor.build()

    assert constructor.get(BranchDep).dep.name == "hello world"
    assert app.dep.name == "foobar"


def test_add_as():
    constructor = Constructor(App)
    constructor.add_as(DependencyB("foobar"), Dependency)
    app = constructor.build()

    assert app.dep.name == "__foobar__"


def test_factories():
    class Dep:
        def __init__(self, name):
            self.name = f"__{name}__"

    class App(Injectable):
        factory: Factory[Dep]

    app = Constructor(App).build()
    assert app.factory("foobar").name == "__foobar__"
