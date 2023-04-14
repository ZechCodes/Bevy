from typing import Any, Generic, Type, TypeVar
from inspect import get_annotations
from bevy.repository import get_repository
import sys

_NOTSET = object()
_T = TypeVar("_T")


class Dependency(Generic[_T]):
    def __init__(self):
        self._type: Type[_T] = _NOTSET

    def __get__(self, instance: object, owner: Type):
        if self._type is _NOTSET:
            raise Exception("The dependency has not been setup")

        repo = get_repository()
        return repo.get(self._type)

    def __set_name__(self, owner: Type, name: str):
        self._type = get_annotations(owner, globals=_get_class_namespace(owner), eval_str=True)[name]


def dependency() -> Any:
    return Dependency()


def _get_class_namespace(cls: Type) -> dict[str, Any]:
    try:
        return vars(sys.modules[cls.__module__])
    except KeyError:
        return {}
