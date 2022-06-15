from bevy import Bevy, Context, Inject
from bevy.providers import TypeProvider
from bevy.providers.function_provider import FunctionProvider, bevy_method
from asyncio import run as run_async


class Dependency:
    def __init__(self, value=-1):
        self.value = value


def test_dependency_creation():
    class Test(Bevy):
        dep: Dependency = Inject()

    test = Test()
    assert isinstance(test.dep, Dependency)


def test_dependency_detection():
    class Test(Bevy, inject=Inject.ALL):
        dep: Dependency

    test = Test()
    assert isinstance(test.dep, Dependency)


def test_dependency_only_detection():
    class Test(Bevy, inject=Inject.ONLY("dep")):
        dep: Dependency
        no_dep: Dependency

    test = Test()
    assert isinstance(test.dep, Dependency)
    assert not hasattr(test, "no_dep")


def test_dependency_ignore_detection():
    class Test(Bevy, inject=Inject.IGNORE("no_dep")):
        dep: Dependency
        no_dep: Dependency

    test = Test()
    assert isinstance(test.dep, Dependency)
    assert not hasattr(test, "no_dep")


def test_shared_dependencies():
    class TestA(Bevy, inject=Inject.ALL):
        dep: Dependency

    class TestB(Bevy, inject=Inject.ALL):
        dep: Dependency

    context = Context.factory()
    a = context.create(TestA)
    b = context.create(TestB)
    assert isinstance(a.dep, Dependency)
    assert isinstance(b.dep, Dependency)
    assert a.dep is b.dep


def test_inherited_dependencies():
    class Test(Bevy, inject=Inject.ALL):
        dep: Dependency

    parent = Context.factory()
    parent.create(Dependency, add_to_context=True)
    child = parent.branch()
    test = child.create(Test)
    assert test.dep is parent.get(Dependency)


def test_multiple_branches_are_isolated():
    class Test(Bevy, inject=Inject.ALL):
        dep: Dependency

    parent = Context.factory()
    child_a = parent.branch()
    test_a = child_a.create(Test)

    child_b = parent.branch()
    test_b = child_b.create(Test)
    test_c = child_b.create(Test)

    assert test_a.dep is not test_b.dep
    assert test_b.dep is test_c.dep


def test_string_annotations():
    class Test(Bevy, inject=Inject.ALL):
        dep: "Dependency"

    test = Test()

    assert isinstance(test.dep, Dependency)


def test_context_descriptor():
    class Test(Bevy):
        def __init__(self):
            self.dep = self.bevy.create(Dependency)

    test = Test()
    assert isinstance(test.dep, Dependency)


def test_context_descriptor_gives_bound_context():
    class Test(Bevy):
        ...

    context = Context.factory()
    test = context.create(Test)
    assert test.bevy is context


def test_unique_creates():
    class Test(Bevy):
        ...

    context = Context.factory()
    test_a = context.create(Test)
    test_b = context.create(Test)

    assert test_a is not test_b


def test_custom_provider():
    class TestProvider(TypeProvider):
        def __init__(self, add):
            super().__init__()
            self._add = add

        def create(self, obj, value=0, *args, add: bool = False, **kwargs):
            return super().create(obj, value + self._add, *args, add=add, **kwargs)

        def supports(self, obj) -> bool:
            return obj is Dependency or issubclass(obj, Dependency)

        @classmethod
        def create_and_insert(cls, providers, add=0, *args, **kwargs):
            return cls(add), *providers

    context = Context.factory()
    context.add_provider(TestProvider, 10)
    test_none = context.get(Dependency)
    test_a = context.create(Dependency, 10, add_to_context=True)
    test_b = context.get(Dependency)
    test_c = context.create(Dependency, 10)

    assert test_none is None
    assert test_a is test_b
    assert test_a is not test_c
    assert (
        test_a.value == test_b.value
        and test_b.value == test_c.value
        and test_c.value == 20
    )


def test_providers_are_inherited():
    class TestProvider(TypeProvider):
        def __init__(self, add):
            super().__init__()
            self._add = add

        def create(self, obj, value=0, *args, add: bool = False, **kwargs):
            return super().create(obj, value + self._add, *args, add=add, **kwargs)

        def supports(self, obj) -> bool:
            return obj is Dependency or issubclass(obj, Dependency)

        @classmethod
        def create_and_insert(cls, providers, *args, **kwargs):
            return cls(*args, **kwargs), *providers

    context = Context.factory()
    context.add_provider(TestProvider, 10)
    branch = context.branch()
    test = branch.create(Dependency, 10)

    assert test.value == 20


def test_function_provider_signature_matching():
    def func_a(x: int, y: str) -> list[int]:
        return [x * 2, int(y)]

    def func_b(a: int, b: str) -> list[int]:
        return [a * 5, int(b) + 2]

    context = Context.factory()
    context.add_provider(FunctionProvider)
    context.add(func_a)
    test = context.get(func_b)
    assert isinstance(context.get_provider_for(func_b), FunctionProvider)
    assert test(5, "10") == [10, 10]
    assert test is func_a


def test_function_injection():
    def func(x: Dependency = Inject) -> int:
        return x.value

    context = Context.factory()
    context.add_provider(FunctionProvider)
    context.add(Dependency(10), use_as=Dependency)
    test = context.bind(func)

    assert test() == 10


def test_coroutine_injection():
    async def func(x: Dependency = Inject) -> int:
        return x.value

    context = Context.factory()
    context.add_provider(FunctionProvider)
    context.add(Dependency(10), use_as=Dependency)
    test = context.bind(func)

    assert run_async(test()) == 10


def test_method_injection():
    class Test:
        def func(self, x: Dependency = Inject) -> int:
            return x.value

    context = Context.factory()
    context.add_provider(FunctionProvider)
    context.add(Dependency(10), use_as=Dependency)

    inst = Test()
    test = context.bind(inst.func)

    assert test() == 10


def test_bevy_method_decorator():
    class Test(Bevy):
        @bevy_method
        def func(self, x: Dependency = Inject) -> int:
            return x.value

    context = Context.factory()
    context.add(Dependency(10), use_as=Dependency)

    test = context.create(Test)
    assert test.func() == 10


def test_function_not_added():
    context = Context.factory()
    func = context.get(open)
    assert func is open
