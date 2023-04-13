from bevy import dependency, inject, Repository, get_repository
from bevy.type_provider import TypeProvider

from pytest import fixture


@fixture
def repository():
    Repository._bevy_repository.set(Repository())
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
