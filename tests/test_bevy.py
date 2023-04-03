from bevy import Context, get_context


def test_context_exists():
    assert isinstance(get_context(), Context)
