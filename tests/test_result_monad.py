from bevy.results import Result, Success, Failure, ResultBuilder


def test_result_set():
    assert Success("Testing")


def test_exception_set():
    assert not Failure(Exception("Testing"))


def test_result_builder_success():
    with ResultBuilder() as (builder, set_result):
        set_result("Testing")

    match builder.result:
        case Success(result):
            assert result == "Testing"
        case _:
            assert False


def test_result_builder_failure():
    with ResultBuilder() as (builder, set_result):
        raise Exception("Testing")

    match builder.result:
        case Failure(Exception() as exception):
            assert exception.args == ("Testing",)
        case _:
            assert False
