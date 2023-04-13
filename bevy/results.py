from typing import Callable, Generic, Self, TypeAlias, TypeVar


T = TypeVar("_T")
Setter: TypeAlias = Callable[[T], None]


class ResultBuilder(Generic[T]):
    def __init__(self):
        self.result: Result[T] = Result[T]()

    def set(self, result: T) -> T:
        self.result = Success[T](result)
        return result

    def __enter__(self) -> tuple[Self, Setter]:
        return self, self.set

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val:
            self.result = Failure[T](exc_val)

        return True


class Result(Generic[T]):
    result: T | None = None
    exception: Exception | None = None

    def __bool__(self):
        return True


class Success(Result[T]):
    __match_args__ = ("result",)

    def __init__(self, result: T):
        self.result = result


class Failure(Result[T]):
    __match_args__ = ("exception",)

    def __init__(self, exception: Exception):
        self.exception = exception

    def __bool__(self):
        return False

    @property
    def result(self) -> T:
        raise self.exception
