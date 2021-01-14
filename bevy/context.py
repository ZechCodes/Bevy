"""Bevy's Contexts manage tracking instances that have been created and injecting the necessary dependencies when new
instances are created.

Contexts

Bevy provides a basic context type. The standard context will add any object to its repository and inject them when
necessary. The context will only attempt to inject into objects being instantiated that inherit from bevy.Injectable.

Injection

All the basic context types built into Bevy handle injection by using a metaclass which overrides the object type's
dunder call method. It then adds a step between dunder new being called and dunder init, in this step it injects the
dependencies. So if a class defines a dunder new it will not have access to any attributes that need to be injected.
When dunder init is called all injections will have been made.

Using a metaclass allows for the class instantiation lifecycle to be modified without ever having to change the
structure of the classes themselves. Bevy doesn't require any state to be stored on a class object and it never needs to
inject anything that isn't specifically defined in the class definition. So Bevy has no impact on the memory foot print
of class objects or on the performance of the class after it's been instantiated.

Injecting The Context

If an object needs access to the context that created it (useful for branching or adding instantiated dependencies) it's
possible to just add an annotation for any subclass of BaseContext. Here's an example:

    class Example(Injectable):
        context: Context

Repository

The context stores every instance that's been created as a dependency in a repository. When a class is found that has a
dependency annotation Bevy checks the repository for any instances that are of the same type or that are a subclass of
that annotation. If no match is found it will create an instance by calling the type with no parameters.

If more advanced instantiation is required for a dependency it is possible to add an instance to the context using
Context.add. That will add the instance to the repository for use in injections. It is then possible to instantiate an
object with the context using Context.create. Here's an example:

    context = Context()
    context.add(PostgresDB(host, port, username, password, database))
    app = context.create(MyWebsiteApp, "My Website", "www.mywebsite.com")

That will add a postgres database object with the necessary connection details to the repository. It will then create an
instance of the MyWebsiteApp class with two parameters and any dependencies injected. Context.create will not add the
instance created to the repository, that can be accomplished by passing the returned instance to Context.add.

Repository Instance Conflicts

The context retrieves the first instance that passes an issubclass check. This means if there are two instances with a
shared MRO it will not be clearly defined which should be used if a super class of both is requested. To prevent this
from happening the context will raise ConflictingTypeAddedToRepository when an instance is added and it is the same
type, a super type of, or a sub type of any instanec already in the repository.

Branching

It is possible to branch a context. This will allow the dependencies on the root context to be used by the branch
context. Dependency instances created on the branch context however will not be available to the root context. This is
useful for preventing the dependencies of a plugin, for example, from polluting the root context and other plugins which
may have their own custom dependencies classes or may need a differently configured instance.
"""

from __future__ import annotations
from bevy.factory import FactoryAnnotation
from typing import Any, Dict, Optional, Type, TypeVar, Union
from functools import lru_cache
import bevy
import sys


T = TypeVar("T")

# Using a singleton to represent unset values simplifies the context API since None no longer has an internal meaning
NO_VALUE = type(
    "NO_VALUE", tuple(), {"__repr__": lambda self: "<NO_VALUE>", "__slots__": []}
)()


class ConflictingTypeAddedToRepository(Exception):
    def __init__(self, attempted_to_add: Any, conflicts_with: Any):
        super().__init__(
            f"{attempted_to_add} conflicts with {conflicts_with} which is already in the repository"
        )


class Context:
    """Contexts are used as a factory for creating instances of classes that have their required dependencies injected.
    The context then stores the instances used to fulfill the requirements in a repository so they can be used again if
    any other class instance requires them. This allows all instances created by a context to share the same
    dependencies.

    Contexts also allow for pre-initialized instances to be added to the repository which will later be used to fulfill
    dependency requirements. This provides for more complex initialization of dependencies, such as for connecting to a
    database.

    Additionally each context has the ability to branch off sub-contexts. The context will share its dependency
    repository with the sub-contexts but any new dependencies created by the sub-contexts will not be propagated back.
    This allows for isolating objects that may have similar dependency requirements but that should have distinct
    dependency instances.

    The context can inject itself as a dependency if a class requires the context's type.

    The base Context type will only inject into objects that are derived from bevy.Injectable."""

    def __init__(self, parent: Context = None):
        self._parent = parent
        self._repository: Dict[Type[T], T] = {}

        self.add(self)

    def add(self, instance: T) -> Context:
        """Adds a pre-initialized instance to the context's repository.

        This will raise ConflictingTypeAddedToRepository if the instance being added is the same type as or a subclass
        of an instance already in the repository."""
        conflict = self.find_conflicting_type(type(instance))
        if conflict:
            raise ConflictingTypeAddedToRepository(instance, self.get(conflict))

        self._repository[type(instance)] = instance
        return self

    def branch(self) -> Context:
        """Creates a new context and adds the current context as its parent. The new context will have access to the
        repository of the branched context, new dependencies that it creates will not be propagated. This is useful for
        isolating instances that may have similar dependencies but that should have distinct dependency instances."""
        return type(self)(self)

    def create(self, object_type: Type[T], *args, **kwargs) -> T:
        """Creates an instance of an object using the current context's repository to fulfill all required
        dependencies. For any dependencies not found in the repository the context will attempt to initialize them
        without any arguments."""
        if not self._can_inject(object_type):
            return object_type(*args, **kwargs)

        return self._create_instance(object_type, args, kwargs)

    def get(
        self, object_type: Type[T], *, default: Any = NO_VALUE, propagate: bool = True
    ) -> Optional[T]:
        """Get's an instance matching the requested type from the context. If default is not set and no match is found
        this will attempt to create an instance by calling the requested type with no arguments. The returned instance
        maybe a subclass of the type but it will never be a superclass. If propagation is allowed and no match is found
        it will attempt to find a match by propagating up through the parent contexts.
        """
        if self.has(object_type, propagate=False):
            return self._find(object_type)

        if propagate and self._parent and self._parent.has(object_type):
            return self._parent.get(object_type, default=default)

        if default is NO_VALUE:
            instance = self.create(object_type)
            self.add(instance)
            return instance

        return default

    def has(self, object_type: Type[T], *, propagate: bool = True) -> bool:
        """ Checks if an instance matching the requested type exists in the context or one of its parent contexts. """
        if self._find(object_type) is NO_VALUE:
            return propagate and self._parent and self._parent.has(object_type)

        return True

    def find_conflicting_type(self, search_for_type: Type[T]) -> Union[Type, bool]:
        """Finds any type that may conflict with the given type. A type is considered conflicting if it is the same
        type, a super type, or a sub type of any instance already in the repository."""
        for t in self._repository:
            if (
                t is search_for_type
                or issubclass(search_for_type, t)
                or issubclass(t, search_for_type)
            ):
                return t

        return False

    def _can_inject(self, object_type: Type[T]) -> bool:
        return issubclass(object_type, bevy.Injectable)

    def _create_instance(self, object_type: Type[T], args, kwargs) -> T:
        instance = object_type.__new__(object_type, *args, **kwargs)
        self._inject(instance)
        instance.__init__(*args, **kwargs)
        return instance

    def _find(self, object_type: Type[T]) -> Union[T, NO_VALUE]:
        """Finds an instance that is either of the requested type or a sub-type of that type. If it is not found
        NO_VALUE will be returned."""
        for repo_type in self._repository:
            if issubclass(repo_type, object_type):
                return self._repository[repo_type]

        return NO_VALUE

    @lru_cache()
    def _find_dependencies(self, object_type: Type) -> Dict[str, Type[T]]:
        dependencies: Dict[str, Type[T]] = {}
        for cls in reversed(object_type.mro()):
            dependencies.update(
                {
                    name: self._resolve_dependency(cls, annotation_type)
                    for name, annotation_type in getattr(
                        cls, "__annotations__", {}
                    ).items()
                    if not hasattr(cls, name)
                }
            )

        return dependencies

    def _inject(self, instance: T):
        for name, dependency in self._find_dependencies(type(instance)).items():
            if isinstance(dependency, FactoryAnnotation):
                value = dependency.create_factory(self)
            else:
                value = self.get(dependency)

            setattr(instance, name, value)

    @lru_cache()
    def _resolve_dependency(self, cls: Type, annotation: Union[str, Type]) -> Type:
        if isinstance(annotation, str):
            module = sys.modules[cls.__module__]
            return eval(annotation, module.__dict__)

        return annotation
