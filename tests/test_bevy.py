from bevy import Repository, get_repository


def test_repository_exists():
    assert isinstance(get_repository(), Repository)
