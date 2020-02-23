from __future__ import annotations
from exo.repository import GenericRepository, Repository
from typing import Any, Dict, Optional, Tuple, Type, Union


class ExoMeta(type):
    _dependencies: Dict[Type[Exo], Dict[str, Type]] = {}

    def __new__(mcs, name: str, bases: Tuple[Type], attrs: Dict[str, Any]):
        """ Find and inherit all dependencies. """
        cls = super().__new__(mcs, name, bases, attrs)
        mcs._dependencies[cls] = mcs._build_dependencies(attrs, bases)
        return cls

    def __call__(cls: Type[Exo], *args: Tuple[Any], **kwargs: Dict[str, Any]) -> Exo:
        return ExoMeta.builder(cls).build(*args, **kwargs)

    def declare(cls: Type[Exo], *args: Tuple[Any]) -> ExoBuilder:
        """ Creates a builder and passes it the declared dependencies. """
        builder = ExoMeta.builder(cls)
        builder.declare(*args)
        return builder

    @classmethod
    def builder(mcs, cls: Type[Exo]) -> ExoBuilder:
        builder = ExoBuilder(cls)
        builder.dependencies(**mcs._dependencies.get(cls, {}))
        return builder

    @classmethod
    def _build_dependencies(
        mcs, attrs: Dict[str, Any], bases: Tuple[Union[Type[Exo], Type]]
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


class Exo(metaclass=ExoMeta):
    def __new__(cls, *args, **kwargs):
        return super().__new__(cls, *args, **kwargs)

    def __init__(self, *args, **kwargs):
        ...


class ExoBuilder:
    def __init__(
        self, cls: Type[Exo], *, repository: Optional[Type[Repository]] = None
    ):
        self._cls = cls
        self._dependencies = {}
        self._repo = Repository.create(repository)

    def build(self, *args: Tuple[Any], **kwargs: Dict[str, Any]) -> Exo:
        """ Builds an instance of the class which has its dependencies
        resolved and injected. """
        instance = self._cls.__new__(self._cls, *args, **kwargs)
        if instance.__class__ is self._cls:
            dependencies = self._resolve_dependencies()
            self._inject_dependencies(instance, dependencies)
            instance.__init__(*args, **kwargs)
        return instance

    def declare(self, *args: Tuple[Any]):
        """ Allows for initialized instances to be declared for use
        during dependency resolution. Useful for configuring a dependency
        at the top level of an app for use by app components. """
        for declaration in args:
            self._repo.set(declaration)

    def dependencies(self, **kwargs: Dict[str, Type]):
        """ Allows for dependencies to be added in an imperative fashion.
        """
        self._dependencies.update(kwargs)

    @staticmethod
    def _inject_dependencies(instance: Exo, dependencies: Dict[str, Any]):
        for name, dependency in dependencies.items():
            setattr(instance, name, dependency)

    def _resolve_dependencies(self) -> Dict[str, Any]:
        return {
            name: self._repo.get(dependency)
            for name, dependency in self._dependencies.items()
        }
