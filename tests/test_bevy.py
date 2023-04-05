from bevy import Repository, get_repository


def test_repository_exists():
    assert isinstance(get_repository(), Repository)


def test_repository_get():
    class TestType:
        ...

    repo = get_repository()
    instance = repo.get(TestType)

    assert isinstance(instance, TestType)


def test_repository_caching():
    class TestType:
        ...

    repo = get_repository()
    instance_a = repo.get(TestType)
    instance_b = repo.get(TestType)

    assert instance_a is instance_b
