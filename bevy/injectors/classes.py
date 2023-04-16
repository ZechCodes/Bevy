import sys
from inspect import get_annotations
from typing import Any, Generic, Type, TypeVar

from bevy.options import Option, Value, Null
from bevy.repository import get_repository

_K = TypeVar("_K")


class Dependency(Generic[_K]):

    def __init__(self):
        self._key: Option[_K] = Null()

    def __get__(self, instance: object, owner: Type):
        match self._key:
            case Value(key):
                repo = get_repository()
                return repo.get(key)

            case Null():
                raise Exception("The dependency has not been setup")

    def __set_name__(self, owner: Type, name: str):
        ns = _get_class_namespace(owner)
        annotations = get_annotations(owner, globals=ns, eval_str=True)
        self._key = Value(annotations[name])


def dependency() -> Any:
    return Dependency()


def _get_class_namespace(cls: Type) -> dict[str, Any]:
    try:
        return vars(sys.modules[cls.__module__])
    except KeyError:
        return {}
