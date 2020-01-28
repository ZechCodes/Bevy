from __future__ import annotations
from abc import ABCMeta
from exo.repositories import ExoRepository
from typing import Callable, Type, TypeVar, Union


ExoComposable = TypeVar("ExoComposable", bound="Composable")


class ComposableMeta(ABCMeta):
    def __call__(
        cls: Type[ExoComposable], *args, __repository__: ExoRepository, **kwargs
    ) -> ExoComposable:
        instance = cls.__new__(cls, *args, **kwargs)
        if instance.__class__ is cls:
            instance.__inject__(__repository__)
            instance.__init__(*args, **kwargs)
        return instance


class Composable(metaclass=ComposableMeta):
    __dependencies__ = {}

    def __inject__(self, repository: ExoRepository) -> None:
        """ Injects dependencies from a repository. This method is called
        before __init__"""
        for name, dependency in self.__class__.__dependencies__.items():
            setattr(self, name, repository.get(dependency))

    @classmethod
    def create(
        cls: Type[ExoComposable], repository: ExoRepository, *args, **kwargs
    ) -> ExoComposable:
        return cls(*args, __repository__=repository, **kwargs)


class NotComposable(Exception):
    ...


def uses(
    composable: Type[ExoComposable] = None, **kwargs
) -> Union[Callable, Type[ExoComposable]]:
    """ Class decorator for defining dependencies of a composable object.

    This will only work on classes that inherit the exo.composables.Composable
    class.

    Can also be called directly with a first argument that is a composable that
    the dependencies should be applied to.

    The dependencies are defined as key/value pairs using keyword arguments.
    The keyword used will be the name of the instance when it is injected into
    the composable at instantiation. The value should be the class that is to
    be instantiated, stored in an exo.repositories.Repository instance, and
    then injected from the repository. """

    def apply(cls: Type[ExoComposable]) -> Type[ExoComposable]:
        if not hasattr(cls, "__dependencies__"):
            raise NotComposable(f"{cls.__name__} is not a valid composable object.")

        cls.__dependencies__.update(kwargs)
        return cls

    return apply(composable) if composable else apply
