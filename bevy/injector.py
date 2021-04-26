from __future__ import annotations
from typing import Protocol, Type, TypeVar


T = TypeVar("T")


class InjectorProtocol(Protocol):
    """Dependency classes can implement this protocol to provide customized instances. The classmethod __bevy_inject__
    will be called at injection time by the context. It will be passed the context, the partial instance that is being
    inject into, and all arguments passed in to the constructor. It should return an instance of the dependency class.
    """

    @classmethod
    def __bevy_inject__(cls: Type[T], context, instance, *args, **kwargs) -> T:
        return


def is_injector(obj: InjectorProtocol) -> bool:
    """Checks if a class object is a valid injector class."""
    if not hasattr(obj, "__bevy_inject__"):
        return False

    if not hasattr(obj.__bevy_inject__, "__self__"):
        return False

    return isinstance(obj.__bevy_inject__.__self__, type)


def is_almost_injector(obj: InjectorProtocol) -> bool:
    """Checks if a class object is almost a valid injector class. It will be almost valid if it has the __bevy_inject__
    method but the method isn't a classmethod."""
    if not hasattr(obj, "__bevy_inject__"):
        return False

    if not hasattr(obj.__bevy_inject__, "__self__"):
        return True

    return not isinstance(obj.__bevy_inject__.__self__, type)
