from __future__ import annotations
from bevy.context import Context
from typing import Any, Dict, Optional, Tuple, Type, Union


class BevyMeta(type):
    _dependencies: Dict[Type[Bevy], Dict[str, Type]] = {}

    def __new__(mcs, name: str, bases: Tuple[Type], attrs: Dict[str, Any]):
        """ Find and inherit all dependencies. """
        cls = super().__new__(mcs, name, bases, attrs)
        mcs._dependencies[cls] = mcs._build_dependencies(attrs, bases)
        return cls

    def __call__(cls: Type[Bevy], *args: Tuple[Any], **kwargs: Dict[str, Any]) -> Bevy:
        return BevyMeta.builder(cls).build(*args, **kwargs)

    def context(cls: Type[Bevy], *args: Tuple[Any]) -> BevyBuilder:
        """ Declares dependencies in a context using a bevy builder. """
        builder = BevyMeta.builder(cls)
        builder.context(*args)
        return builder

    @classmethod
    def builder(mcs, cls: Type[Bevy], context: Optional[Context] = None) -> BevyBuilder:
        builder = BevyBuilder(cls, context=context)
        builder.dependencies(**mcs._dependencies.get(cls, {}))
        return builder

    @classmethod
    def _build_dependencies(
        mcs, attrs: Dict[str, Any], bases: Tuple[Union[Type[Bevy], Type]]
    ) -> Dict[str, Type]:
        """ Builds a dictionary of dependencies from the annotated properties
        that are found on the bases and in the class definition. These
        dependencies are stored in the __dependencies__ attribute of the class.
        """
        dependencies = {}
        for base in bases:
            if base in mcs._dependencies:
                dependencies.update(mcs._dependencies[base])

        dependencies.update(
            {
                name: dependency
                for name, dependency in attrs.get("__annotations__", {}).items()
                if name not in attrs
            }
        )

        return dependencies


class Bevy(metaclass=BevyMeta):
    def __new__(cls, *args, **kwargs):
        return super().__new__(cls, *args, **kwargs)


class BevyBuilder:
    def __init__(
        self,
        cls: Type[Bevy],
        *,
        context: Optional[Union[Type[Context], Context]] = None
    ):
        self._cls = cls
        self._dependencies = {}
        self._repo = Context.create(context)

    def build(self, *args: Tuple[Any], **kwargs: Dict[str, Any]) -> Bevy:
        """ Builds an instance of the class which has its dependencies
        resolved and injected. """
        instance = self._cls.__new__(self._cls, *args, **kwargs)
        if instance.__class__ is self._cls:
            dependencies = self._resolve_dependencies()
            self._inject_dependencies(instance, dependencies)
            instance.__init__(*args, **kwargs)
        return instance

    def context(self, *args: Tuple[Any]):
        """ Allows for initialized instances to be declared in the context for
        use during dependency resolution. Useful for configuring a dependency
        at the top level of an app for use by app components. """
        for declaration in args:
            self._repo.set(declaration)

    def dependencies(self, **kwargs: Dict[str, Type]):
        """ Allows for dependencies to be added in an imperative fashion.
        """
        self._dependencies.update(kwargs)

    @staticmethod
    def _inject_dependencies(instance: Bevy, dependencies: Dict[str, Any]):
        for name, dependency in dependencies.items():
            setattr(instance, name, dependency)

    def _resolve_dependencies(self) -> Dict[str, Any]:
        return {
            name: self._repo.get(dependency)
            for name, dependency in self._dependencies.items()
        }
