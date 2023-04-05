from typing import Callable, Generic, Self, TypeAlias, TypeVar


T = TypeVar("T")
Setter: TypeAlias = Callable[[T], None]
_NOTSET = object()


class ResultBuilder(Generic[T]):
    def __init__(self):
        self.result: Result[T] = Result[T]()

    def set(self, result: T):
        self.result = Success[T](result)

    def __enter__(self) -> tuple[Self, Setter]:
        return self, self.set

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val:
            self.result = Failure[T](exc_val)

        return True


class Result(Generic[T]):
    _result: T | None = _NOTSET
    exception: Exception | None = None

    @property
    def result(self) -> T:
        if self.exception:
            raise self.exception

        return self._result

    def __bool__(self):
        return self.exception is None and self._result is not _NOTSET


class Success(Result[T]):
    __match_args__ = ("result",)

    def __init__(self, result: T):
        self._result = result


class Failure(Result[T]):
    __match_args__ = ("exception",)

    def __init__(self, exception: Exception):
        self.exception = exception
