import sys
from inspect import get_annotations
from typing import Any, Generic, Type, TypeVar

from bevy.options import Option, Value, Null
from bevy.repository import get_repository

_K = TypeVar("_K")


class Dependency(Generic[_K]):
    """This class can be used to indicate fields that need to be injected. It also acts as a descriptor that can
    discover the key that needs to be injected and handle injecting the corresponding instance for that key when
    accessed.

    To avoid typing errors that may arise from assigning instances of `Dependency` to fields, use the `dependency`
    function. That function returns a new instance of `Dependency` but has a return type of `typing.Any`.
    """

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
    """This helper function allows instances of the `Dependency` type to be assigned to fields without breaking type
    checking."""
    return Dependency()


def _get_class_namespace(cls: Type) -> dict[str, Any]:
    """Attempts to get the global variables in the module that a class was declared in."""
    try:
        return vars(sys.modules[cls.__module__])
    except KeyError:
        return {}
