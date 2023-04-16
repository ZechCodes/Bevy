from functools import wraps
from typing import Callable, Generic, ParamSpec, Self, TypeAlias, TypeVar

_P = ParamSpec("_P")
_R = TypeVar("_R")
_T = TypeVar("_T")
Setter: TypeAlias = Callable[[_T], None]


class Result(Generic[_T]):
    result: _T | None = None
    exception: Exception | None = None

    def __bool__(self):
        return True


class Success(Result[_T]):
    __match_args__ = ("result",)

    def __init__(self, result: _T):
        self.result = result


class Failure(Result[_T]):
    __match_args__ = ("exception",)

    def __init__(self, exception: Exception):
        self.exception = exception

    def __bool__(self):
        return False

    @property
    def result(self) -> _T:
        raise self.exception


class ResultBuilder(Generic[_T]):
    def __init__(self):
        self.result: Result[_T] = Result[_T]()

    def set(self, result: _T | Result[_T]) -> _T:
        match result:
            case Result() as r:
                self.result = result
            case _ as r:
                self.result = Success[_T](result)

        return result

    def __enter__(self) -> tuple[Self, Setter]:
        return self, self.set

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val:
            self.result = Failure[_T](exc_val)

        return True


def result(func: Callable[_P, _R]) -> Callable[_P, _R]:
    @wraps(func)
    def result_wrapper(*args: _P.args, **kwargs: _P.kwargs) -> Result[_R]:
        with ResultBuilder() as (builder, set_result):
            match func(*args, **kwargs):
                case Result() as r:
                    set_result(r)
                case _ as r:
                    set_result(Success(r))

        return builder.result

    return result_wrapper
