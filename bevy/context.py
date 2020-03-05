from __future__ import annotations
from typing import Any, Dict, Optional, Type, TypeVar, Union
import bevy.bevy as bevy
import enum


GenericContext = TypeVar("GenericContext", bound="Context")
GenericInstance = TypeVar("GenericInstance")
GenericType = Type[GenericInstance]
_NOVAL = object()


class Strategy(enum.Enum):
    INHERIT = enum.auto()
    NO_INHERIT = enum.auto()
    ALWAYS_CREATE = enum.auto()


class Context:
    strategy = Strategy

    def __init__(self, parent: Optional[GenericContext] = None):
        self._parent = parent
        self._instance_repo: Dict[GenericType, GenericInstance] = {self.__class__: self}

    def create_scope(self) -> GenericContext:
        """ Creates a context using the parent's type and passes the parent
        to the new context. """
        return type(self)(self)

    def get(
        self, obj: GenericType, *, default: Any = _NOVAL, propagate: bool = True
    ) -> Optional[GenericInstance]:
        """ Get's an instance matching the requested type from the context.
        If default is not set and an match is not found this will create an
        instance using the requested type. """
        if propagate and self._can_inherit(obj):
            return self._parent.get(obj, default=default)

        if not self.has(obj, propagate=False):
            if default is not _NOVAL:
                return default
            return self.set(obj, obj)
        return self._find(obj)

    def has(
        self, obj: Union[GenericType, GenericInstance], *, propagate: bool = True
    ) -> bool:
        """ Checks if an instance matching the requested type exists in the
        context. If a type is not provided this will raise an exception. """
        if not isinstance(obj, type):
            obj = type(obj)

        return self._find(obj) is not _NOVAL or (
            propagate and self._parent and self._parent.has(obj)
        )

    def set(
        self,
        look_up_type: Union[GenericType, GenericInstance],
        instance: Optional[Union[GenericType, GenericInstance]] = None,
    ) -> GenericInstance:
        """ Sets the instance that should be returned when a given type is
        requested. This will raise exceptions if the look up type isn't a type
        and if the instance type is not an instance of the look up type. """
        if not isinstance(look_up_type, type):
            instance = look_up_type
            look_up_type = type(instance)

        elif not instance:
            instance = look_up_type

        value = instance
        if isinstance(instance, type):
            value = (
                bevy.BevyMeta.builder(instance, context=self).build()
                if issubclass(instance, bevy.Bevy)
                else instance()
            )

        if not isinstance(value, look_up_type):
            raise BevyContextMustBeMatchingTypes(
                f"Cannot set a value for mismatched types, received {look_up_type} and {instance}"
            )

        strategy = getattr(look_up_type, "__context_strategy__", Strategy.INHERIT)
        if strategy != Strategy.ALWAYS_CREATE:
            self._instance_repo[look_up_type] = value

        return value

    def _can_inherit(self, look_up_type: GenericType) -> bool:
        if not self._parent:
            return False

        strategy = getattr(look_up_type, "__context_strategy__", Strategy.INHERIT)
        if strategy != Strategy.INHERIT:
            return False

        return not self.has(look_up_type, propagate=False)

    def _find(self, look_up_type: GenericType) -> Union[GenericInstance, _NOVAL]:
        for repo_type in self._instance_repo:
            if issubclass(repo_type, look_up_type):
                return self._instance_repo[repo_type]
        return _NOVAL

    @classmethod
    def create(
        cls,
        repo: Optional[Union[GenericContext, Type[GenericContext]]] = None,
        *args,
        **kwargs,
    ) -> GenericContext:
        """ Return a context object. If the repo provided is already
        instantiated it will be returned without change. If it is a subclass of
        Context it will be instantiated with any args provided and returned.
        If neither of those is true Context will be instantiated with the
        provided args and returned. The return is guaranteed to be an instance
        of Context. """
        if isinstance(repo, Context):
            return repo

        if repo and isinstance(repo, type) and issubclass(repo, Context):
            return repo(*args, **kwargs)

        return cls(*args, **kwargs)


class BevyContextMustBeMatchingTypes(Exception):
    ...
