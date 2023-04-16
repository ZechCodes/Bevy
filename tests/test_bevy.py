from typing import Annotated

from pytest import fixture

from bevy import dependency, inject, Repository, get_repository
from bevy.annotated_provider import AnnotatedProvider
from bevy.type_provider import TypeProvider


@fixture
def repository():
    Repository.set_repository(Repository())
    return get_repository()


def test_repository_exists(repository):
    assert isinstance(get_repository(), Repository)


def test_repository_get(repository):
    class TestType:
        ...

    repository.add_providers(TypeProvider)
    instance = repository.get(TestType)

    assert isinstance(instance, TestType)


def test_repository_caching(repository):
    class TestType:
        ...

    repository.add_providers(TypeProvider)
    instance_a = repository.get(TestType)
    instance_b = repository.get(TestType)

    assert instance_a is instance_b


def test_injection_descriptor(repository):
    class Dep:
        ...

    class TestType:
        dep: Dep = dependency()

    repository.add_providers(TypeProvider)
    instance = TestType()

    assert isinstance(instance.dep, Dep)


def test_injection_descriptor_is_shared(repository):
    class Dep:
        ...

    class TestType:
        dep: Dep = dependency()

    repository.add_providers(TypeProvider)
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

    repository.add_providers(TypeProvider)

    ret_a, ret_b = test_function()
    assert isinstance(ret_a, DepA)
    assert isinstance(ret_b, DepB)


def test_annotated_provider(repository):
    @inject
    def test_function(param: Annotated[str, "Testing"] = dependency()) -> str:
        return param

    repository.add_providers(AnnotatedProvider)
    repository.add(Annotated[str, "Testing"], "testing")

    assert test_function() == "testing"


def test_annotated_provider_on_class(repository):
    class TestType:
        dep: Annotated[str, "Testing"] = dependency()

    repository.add_providers(AnnotatedProvider)
    repository.add(Annotated[str, "Testing"], "testing")
    assert TestType().dep == "testing"


def test_annotated_dependency_not_set(repository):
    @inject
    def test_function(param: Annotated[str, "Testing"] = dependency()) -> str:
        return param

    repository.add_providers(AnnotatedProvider, TypeProvider)
    assert test_function() == ""


def test_multiple_annotated(repository):
    @inject
    def test_function(
        param_a: Annotated[str, "TestA"] = dependency(),
        param_b: Annotated[str, "TestB"] = dependency(),
    ) -> tuple[str, str]:
        return param_a, param_b

    repository.add_providers(AnnotatedProvider)
    repository.add(Annotated[str, "TestA"], "test_a")
    repository.add(Annotated[str, "TestB"], "test_b")

    assert test_function() == ("test_a", "test_b")
