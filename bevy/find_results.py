import asyncio
import concurrent.futures
import contextvars
import inspect
import typing as t
from typing import TYPE_CHECKING, Any

from tramp.optionals import Optional

if TYPE_CHECKING:
    from bevy.containers import Container
    from bevy.injection_types import DependencyResolutionError

from bevy.hooks import Hook


def issubclass_or_raises[T](cls: T, class_or_tuple: t.Type[T] | tuple[t.Type[T], ...], exception: Exception) -> bool:
    """Check if cls is a subclass, raising the provided exception on TypeError."""
    try:
        return issubclass(cls, class_or_tuple)
    except TypeError as e:
        raise exception from e


class Result[T]:
    """Bevy's result types allow values to be fetched from a container in either sync or async contexts."""

    def __init__(self, container: "Container", dependency: t.Type[T], **kwargs):
        """Initialize Result with container context and dependency resolution parameters.

        Args:
            container: The container to resolve dependencies from
            dependency: The type to resolve
            **kwargs: Additional parameters matching container.get() signature
                     (default, default_factory, qualifier, context)
        """
        self.container = container
        self.dependency = dependency
        self.kwargs = kwargs

    def __await__(self):
        return self.get_async().__await__()

    async def _call_factory(self, factory: t.Callable) -> t.Any:
        """
        Call a factory function (sync or async) and await if necessary.

        Supports:
        - Sync factories: lambda: SomeType()
        - Async factories: async def create() -> SomeType
        - Factories with dependencies: def create(dep: Inject[OtherType]) -> SomeType

        Args:
            factory: Factory function to call

        Returns:
            Instance created by factory
        """
        # Check if factory accepts parameters for dependency injection
        factory_sig = inspect.signature(factory)
        if len(factory_sig.parameters) > 0:
            # Factory accepts parameters, use container for dependency injection
            result = self.container.call(factory)
        else:
            # Factory takes no parameters, call directly
            result = factory()

        # Await if result is a coroutine or awaitable
        if inspect.iscoroutine(result):
            return await result
        elif hasattr(result, "__await__"):
            # Awaitable but not a coroutine (e.g., asyncio.Task)
            return await result
        else:
            # Sync result, return as-is
            return result

    def _get_existing_instance(self, dependency: t.Type) -> Optional[Any]:
        """Lookup an existing instance in the container's cache.

        Checks for exact type match first, then subclass matches.
        Skips qualified instances and factory-cached instances.
        """
        if dependency in self.container.instances:
            return Optional.Some(self.container.instances[dependency])

        if not isinstance(dependency, type):
            return Optional.Nothing()

        for instance_type, instance in self.container.instances.items():
            # Skip qualified instances (tuple keys) and factory-cached instances (callable keys)
            if isinstance(instance_type, tuple) or callable(instance_type):
                continue

            if issubclass_or_raises(
                dependency,
                instance_type,
                TypeError(f"Cannot check if {dependency} is a subclass of {instance_type}")
            ):
                return Optional.Some(instance)

        return Optional.Nothing()

    def _find_factory_for_type(self, dependency: t.Type) -> Optional[t.Callable]:
        """Find a factory function that can create instances of the dependency type.

        Searches the registry for a factory registered for this type or a parent type.
        """
        if not isinstance(dependency, type):
            return Optional.Nothing()

        for factory_type, factory in self.container.registry.factories.items():
            if issubclass_or_raises(
                dependency,
                factory_type,
                TypeError(f"Cannot check if {dependency!r} is a subclass of {factory_type!r}")
            ):
                return Optional.Some(factory)

        return Optional.Nothing()

    def _get_factory_cache_result(self, factory: t.Callable) -> Any | None:
        """Get cached result for a factory function, checking parent containers.

        Recursively walks up the parent chain looking for a cached result.
        """
        if factory in self.container.instances:
            return self.container.instances[factory]

        if self.container.parent:
            # Recursively check parent - create a temporary Result for parent lookup
            parent_result = Result(self.container.parent, self.dependency, **self.kwargs)
            return parent_result._get_factory_cache_result(factory)

        return None

    async def _create_instance(self, dependency: t.Type, context: dict[str, Any]) -> tuple[Any, bool]:
        """Create a new instance of the dependency using factories or hooks.

        Uses async hooks natively for truly async dependency resolution.
        Returns (instance, disable_implicit_caching).
        """
        disable_implicit_caching = False

        match await self.container.registry.hooks[Hook.CREATE_INSTANCE].handle(self.container, dependency, context):
            case Optional.Some(v):
                instance = v
                disable_implicit_caching = True  # Hook should handle caching

            case Optional.Nothing():
                match self._find_factory_for_type(dependency):
                    case Optional.Some(factory):
                        # Call factory - handles both sync and async factories
                        result = factory(self.container)
                        # Await if it's a coroutine
                        if inspect.iscoroutine(result):
                            instance = await result
                        elif hasattr(result, "__await__"):
                            instance = await result
                        else:
                            instance = result

                    case Optional.Nothing():
                        instance = await self._handle_unsupported_dependency(dependency, context)
                        disable_implicit_caching = True  # If no error raised, hook should handle caching

                    case _:
                        raise RuntimeError(f"Impossible state reached.")

            case _:
                raise ValueError(
                    f"Invalid value returned from hook for dependency: {dependency}, must be an Optional type."
                )

        filtered_instance = await self.container.registry.hooks[Hook.CREATED_INSTANCE].filter(self.container, instance, context)
        return filtered_instance, disable_implicit_caching

    async def _handle_unsupported_dependency(self, dependency: t.Type, context: dict[str, Any]) -> Any:
        """Handle a dependency that has no factory or existing instance.

        Uses async hooks natively for truly async fallback resolution.
        Delegates to hooks or raises DependencyResolutionError.
        """
        match await self.container.registry.hooks[Hook.HANDLE_UNSUPPORTED_DEPENDENCY].handle(self.container, dependency, context):
            case Optional.Some(v):
                return v

            case Optional.Nothing():
                from bevy.injection_types import DependencyResolutionError

                parameter_name = "unknown"
                if "injection_context" in context:
                    parameter_name = context["injection_context"].parameter_name

                raise DependencyResolutionError(
                    dependency_type=dependency,
                    parameter_name=parameter_name,
                    message=f"No handler found that can handle dependency: {dependency!r}"
                )

            case _:
                raise ValueError(
                    f"Invalid value returned from hook for dependency: {dependency}, must be an Optional type."
                )

    def get(self) -> T:
        """Fetches the value from the container assuming a sync context, utilizing an event loop in a thread to await the result."""
        def run():
            return asyncio.run(self.get_async())

        # Capture context variables
        ctx = contextvars.copy_context()

        # Run in thread with context
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(ctx.run, run)
            try:
                return future.result(timeout=30)
            except concurrent.futures.TimeoutError:
                raise TimeoutError(f"Dependency resolution timed out after 30 seconds")

    async def get_async(self) -> T:
        """Fetches the value from the container in an async context."""
        disable_implicit_caching = False
        default_factory = self.kwargs.get("default_factory", None)
        cache_factory_result = self.kwargs.get("cache_factory_result", True)
        qualifier = self.kwargs.get("qualifier", None)
        context: dict[str, Any] = self.kwargs.get("context", {})

        # Handle qualified dependencies first
        if qualifier:
            qualified_key = (self.dependency, qualifier)

            # Check current container for qualified instance
            if qualified_key in self.container.instances:
                return self.container.instances[qualified_key]

            # Check parent container for qualified instance
            if self.container.parent:
                try:
                    parent_kwargs = {"qualifier": qualifier}
                    if default_factory:
                        parent_kwargs["default_factory"] = default_factory
                    return await self.container.parent.find(self.dependency, **parent_kwargs).get_async()
                except Exception:  # DependencyResolutionError
                    pass

            # If we have a default_factory for qualified dependency, use it
            if default_factory:
                # Check factory cache first (qualified factories use same cache as unqualified)
                if cache_factory_result and default_factory in self.container.instances:
                    return self.container.instances[default_factory]

                # Call factory (handles sync and async factories)
                instance = await self._call_factory(default_factory)

                # Cache using both the factory key and qualified key (if caching enabled)
                if cache_factory_result:
                    self.container.instances[default_factory] = instance
                    self.container.instances[qualified_key] = instance
                return instance
            elif "default" in self.kwargs:
                return self.kwargs["default"]
            else:
                from bevy.injection_types import DependencyResolutionError
                raise DependencyResolutionError(
                    dependency_type=self.dependency,
                    parameter_name="unknown",
                    message=f"Cannot resolve qualified dependency {self.dependency.__name__} with qualifier '{qualifier}'"
                )

        # Handle unqualified dependencies - prioritize default_factory when specified
        if default_factory:
            # Default factory takes precedence over existing instances
            # Check if we already have a cached result from that factory (if caching enabled)
            if cache_factory_result and default_factory in self.container.instances:
                return self.container.instances[default_factory]

            # Check parent container's factory cache (if caching enabled)
            if cache_factory_result and self.container.parent:
                if parent_result := self._get_factory_cache_result(default_factory):
                    # Cache in this container too for faster future access
                    self.container.instances[default_factory] = parent_result
                    return parent_result

            # Call factory (handles sync and async factories)
            instance = await self._call_factory(default_factory)

            # Cache using the factory as the key (if caching enabled)
            if cache_factory_result:
                self.container.instances[default_factory] = instance
            return instance

        # No default factory, use normal resolution with async hooks
        match await self.container.registry.hooks[Hook.GET_INSTANCE].handle(self.container, self.dependency, context):
            case Optional.Some(v):
                instance = v
                disable_implicit_caching = True  # Hook should handle caching

            case Optional.Nothing():
                if dep := self._get_existing_instance(self.dependency):
                    instance = dep.value
                else:
                    dep = None
                    if self.container.parent:
                        # Only check parent for the dependency type, not for factory creation
                        # This ensures sibling container isolation for factory results
                        dep = await self.container.parent.find(self.dependency, default=None).get_async()

                    if dep is None:
                        if "default" in self.kwargs:
                            dep = self.kwargs["default"]
                            disable_implicit_caching = True
                        else:
                            dep, disable_implicit_caching = await self._create_instance(self.dependency, context)

                    instance = dep

            case _:
                raise ValueError(f"Invalid value for dependency: {self.dependency}, must be an Optional type.")

        instance = await self.container.registry.hooks[Hook.GOT_INSTANCE].filter(self.container, instance, context)
        if not disable_implicit_caching:
            self.container.instances[self.dependency] = instance

        return instance
