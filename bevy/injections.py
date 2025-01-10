import typing as t
from functools import update_wrapper

import bevy.containers as containers


class InjectionFunctionWrapper[**P, R]:
    def __init__(self, func: t.Callable[P, R]):
        self._func = func
        update_wrapper(self, func)

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> R:
        return self.call_using(containers.get_container(), *args, **kwargs)

    def call_using(self, container: "containers.Container", *args: P.args, **kwargs: P.kwargs) -> R:
        return container.call(self._func, *args, **kwargs)


def inject[**P, R](func: t.Callable[P, R]) -> InjectionFunctionWrapper[P, R]:
    return InjectionFunctionWrapper(func)
