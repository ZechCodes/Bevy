import sys
from dataclasses import dataclass
from typing import Annotated

from pytest import fixture

from bevy import dependency, inject, Repository, get_repository
from bevy.providers.annotated_provider import AnnotatedProvider
from bevy.providers.type_provider import TypeProvider


class TestRepository(Repository):
    @classmethod
    def factory(cls):
        return cls()


@fixture
def repository():
    Repository.set_repository(TestRepository.factory())
    return get_repository()


def test_repository_exists(repository):
    assert isinstance(get_repository(), Repository)


def test_repository_type_overridden(repository):
    assert isinstance(get_repository(), TestRepository)


def test_repository_get(repository):
    class TestType:
        ...

    repository.add_providers(TypeProvider())
    instance = repository.get(TestType)

    assert isinstance(instance, TestType)


def test_repository_caching(repository):
    class TestType:
        ...

    repository.add_providers(TypeProvider())
    instance_a = repository.get(TestType)
    instance_b = repository.get(TestType)

    assert instance_a is instance_b


def test_injection_descriptor(repository):
    class Dep:
        ...

    class TestType:
        dep: Dep = dependency()

    repository.add_providers(TypeProvider())
    instance = TestType()

    assert isinstance(instance.dep, Dep)


def test_injection_descriptor_is_shared(repository):
    class Dep:
        ...

    class TestType:
        dep: Dep = dependency()

    repository.add_providers(TypeProvider())
    instance_a = TestType()
    instance_b = TestType()

    assert instance_a.dep is instance_b.dep


def test_function_parameter_injection(repository):
    class DepA:
        ...

    class DepB:
        ...

    @inject
    def test_function(param_a: DepA = dependency(), param_b: DepB = dependency()):
        return param_a, param_b

    repository.add_providers(TypeProvider())

    ret_a, ret_b = test_function()
    assert isinstance(ret_a, DepA)
    assert isinstance(ret_b, DepB)


def test_annotated_provider(repository):
    @inject
    def test_function(param: Annotated[str, "Testing"] = dependency()) -> str:
        return param

    repository.add_providers(AnnotatedProvider())
    repository.set(Annotated[str, "Testing"], "testing")

    assert test_function() == "testing"


def test_annotated_provider_on_class(repository):
    class TestType:
        dep: Annotated[str, "Testing"] = dependency()

    repository.add_providers(AnnotatedProvider())
    repository.set(Annotated[str, "Testing"], "testing")
    assert TestType().dep == "testing"


def test_annotated_dependency_not_set(repository):
    @inject
    def test_function(param: Annotated[str, "Testing"] = dependency()) -> str:
        return param

    repository.add_providers(AnnotatedProvider(), TypeProvider())
    assert test_function() == ""


def test_multiple_annotated(repository):
    @inject
    def test_function(
        param_a: Annotated[str, "TestA"] = dependency(),
        param_b: Annotated[str, "TestB"] = dependency(),
    ) -> tuple[str, str]:
        return param_a, param_b

    repository.add_providers(AnnotatedProvider())
    repository.set(Annotated[str, "TestA"], "test_a")
    repository.set(Annotated[str, "TestB"], "test_b")

    assert test_function() == ("test_a", "test_b")


def test_bevy_constructor(repository):
    class Dep:
        def __init__(self, msg: str):
            self.msg = msg

        @classmethod
        def __bevy_constructor__(cls):
            return cls("test")

    @inject
    def test_function(param: Dep = dependency()) -> tuple[str, str]:
        return param.msg

    repository.add_providers(TypeProvider())
    assert test_function() == "test"


def test_repository_branching(repository):
    repository.add_providers(TypeProvider())
    repository.set(int, 10)

    branch = repository.branch()
    assert branch.get(int) is repository.get(int)


def test_repository_branching_no_propagation(repository):
    repository.add_providers(TypeProvider())
    repository.set(int, 10)

    branch = repository.branch()
    assert not branch.find(int, allow_propagation=False)


def test_repository_branching_create(repository):
    repository.add_providers(TypeProvider())
    repository.set(int, 10)

    branch = repository.branch()
    branch.create(int)
    assert branch.find(int).value_or(-1) is 0
    assert repository.find(int).value_or(-1) is 10


def test_context_forking(repository):
    fork = repository.fork_context()
    assert get_repository() is fork
    assert fork is not repository


def test_context_forking_inheritance(repository):
    repository.add_providers(TypeProvider())
    repository.set(int, 10)

    fork = repository.fork_context()
    assert fork.get(int) is repository.get(int)


def test_dataclass_dependency_injection():
    class Dep:
        ...

    @dataclass
    class Test:
        dep: Dep = dependency()

    repo = Repository.factory()
    Repository.set_repository(repo)

    dep = Dep()
    repo.set(Dep, dep)

    inst = Test()
    assert inst.dep is dep


def test_forward_references():
    class Test:
        dep: "Dep" = dependency()

    class Dep:
        ...
