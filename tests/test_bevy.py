from bevy import dependency, Repository, get_repository
from bevy.generic_provider import GenericProvider


def test_repository_exists():
    assert isinstance(get_repository(), Repository)


def test_repository_get():
    class TestType:
        ...

    repo = get_repository()
    repo.add_providers(GenericProvider)
    instance = repo.get(TestType)

    assert isinstance(instance, TestType)


def test_repository_caching():
    class TestType:
        ...

    repo = get_repository()
    repo.add_providers(GenericProvider)
    instance_a = repo.get(TestType)
    instance_b = repo.get(TestType)

    assert instance_a is instance_b


def test_injection_descriptor():
    class Dep:
        ...

    class TestType:
        dep: Dep = dependency()

    repo = get_repository()
    repo.add_providers(GenericProvider)
    instance = TestType()

    assert isinstance(instance.dep, Dep)


def test_injection_descriptor_is_shared():
    class Dep:
        ...

    class TestType:
        dep: Dep = dependency()

    repo = get_repository()
    repo.add_providers(GenericProvider)
    instance_a = TestType()
    instance_b = TestType()

    assert instance_a.dep is instance_b.dep
