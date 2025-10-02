import time
import typing as t
from contextvars import ContextVar
from inspect import signature
from typing import Any

from tramp.optionals import Optional

import bevy.registries as registries
from bevy.context_vars import get_global_container, global_container, GlobalContextMixin
from bevy.debug import create_debug_logger
# DependencyMetadata removed - using injection system
from bevy.find_results import Result
from bevy.hooks import Hook, InjectionContext, PostInjectionContext
from bevy.injection_types import (
    DependencyResolutionError, get_non_none_type, InjectionStrategy, is_optional_type, TypeMatchingStrategy,
)
from bevy.injections import InjectableCallable

type Instance = t.Any

# Context variable to track current injection chain across factory calls
_current_injection_chain: ContextVar[list[str]] = ContextVar('current_injection_chain', default=[])


def issubclass_or_raises[T](cls: T, class_or_tuple: t.Type[T] | tuple[t.Type[T], ...], exception: Exception) -> bool:
    try:
        return issubclass(cls, class_or_tuple)
    except TypeError as e:
        raise exception from e


class Container(GlobalContextMixin, var=global_container):
    """Stores instances for dependencies and provides utilities for injecting dependencies into callables at runtime.

    Containers support hierarchical inheritance through branching, allowing you to create child containers
    that inherit parent instances while maintaining isolation for overrides. This enables powerful patterns
    for testing, request scoping, and environment-specific configurations.
    
    Key Features:
        - **Instance Management**: Store and retrieve dependency instances by type
        - **Dependency Injection**: Automatically inject dependencies into function calls
        - **Container Branching**: Create child containers that inherit from parents
        - **Qualified Dependencies**: Support multiple instances of the same type with qualifiers
        - **Factory Integration**: Work with factory functions for lazy instance creation
        - **Hook System**: Extensible lifecycle hooks for customization
    
    Container Hierarchy:
        When using .branch(), child containers inherit all parent instances but can override them
        without affecting the parent. Resolution always checks the child first, then walks up
        the parent chain until an instance is found.
        
        Example:
            >>> registry = Registry()
            >>> parent = Container(registry)
            >>> parent.add(Logger(level="INFO"))
            >>> 
            >>> child = parent.branch()
            >>> child.add(Logger(level="DEBUG"))  # Override parent's logger
            >>> 
            >>> parent.get(Logger).level   # "INFO" - parent unchanged
            >>> child.get(Logger).level    # "DEBUG" - child override
    
    Common Patterns:
        - **Testing**: Branch production container, override with mocks
        - **Request Scoping**: Branch app container, add request-specific data  
        - **Environment Config**: Branch base config, add environment-specific services
        - **Multi-tenant**: Branch shared infrastructure, add tenant-specific instances
        
    See docs/container-branching.md for comprehensive usage examples.
    """
    def __init__(self, registry: "registries.Registry", *, parent: "Container | None" = None):
        super().__init__()
        self.registry = registry
        # Unified instances cache - can store:
        # - Type -> Instance (regular instances)
        # - (Type, qualifier) -> Instance (qualified instances) 
        # - Callable -> Instance (factory-cached instances)
        self.instances: dict[t.Type[Instance] | tuple | t.Callable, Instance] = {
            Container: self,
            registries.Registry: registry,
        }
        self._parent = parent

    @property
    def parent(self) -> "Container | None":
        """Returns the parent container, or None if this is a root container."""
        return self._parent

    @t.overload
    def add(self, instance: Instance):
        ...

    @t.overload
    def add(self, for_dependency: t.Type[Instance], instance: Instance):
        ...

    @t.overload
    def add(self, for_dependency: t.Type[Instance], instance: Instance, *, qualifier: str):
        ...

    def add(self, *args, **kwargs):
        match args:
            case [instance]:
                self.instances[type(instance)] = instance

            case [for_dependency, instance]:
                qualifier = kwargs.get('qualifier')
                if qualifier:
                    # Store qualified instance with (type, qualifier) key
                    self.instances[(for_dependency, qualifier)] = instance
                else:
                    self.instances[for_dependency] = instance

            case _:
                raise ValueError(f"Unexpected arguments to add: {args}")

    def branch(self) -> "Container":
        """Creates a child container that inherits from this parent container.
        
        Child containers inherit all instances from their parent but can override them without
        affecting the parent. This enables powerful patterns for testing, request scoping,
        and environment-specific configurations.
        
        Inheritance Rules:
            - Child inherits all parent instances and can access them via get() or injection
            - Child can override parent instances by adding instances of the same type
            - Child overrides are isolated - they don't affect the parent or sibling containers
            - Resolution checks child first, then walks up the parent chain
            - Factory caches are inherited - if parent created an instance via factory, child reuses it
            - Qualified instances (instances with qualifiers) inherit independently
        
        Common Use Cases:
        
        Testing - Override production services with mocks:
            >>> # Production setup
            >>> app = Container(registry)
            >>> app.add(DatabaseConnection("postgresql://prod"))
            >>> app.add(EmailService(smtp_config))
            >>> 
            >>> # Test setup - inherit production, override specific services
            >>> test = app.branch()
            >>> test.add(DatabaseConnection("sqlite://memory"))  # Override for testing
            >>> test.add(MockEmailService())  # Override with mock
            >>> # test container now uses test DB and mock email, but inherits everything else
        
        Request Scoping - Add request-specific data while sharing application services:
            >>> # Application container with shared services
            >>> app = Container(registry)
            >>> app.add(DatabasePool())
            >>> app.add(CacheService())
            >>> 
            >>> # Per-request container
            >>> def handle_request(user_id):
            ...     request_container = app.branch()
            ...     request_container.add(CurrentUser(user_id))  # Add request-specific data
            ...     return request_container.call(process_request)
            
        Environment Configuration - Share common setup, override environment specifics:
            >>> # Base configuration
            >>> base = Container(registry)
            >>> base.add(Logger())
            >>> base.add(MetricsCollector())
            >>> 
            >>> # Environment-specific containers
            >>> dev = base.branch()
            >>> dev.add(DatabaseConnection("localhost:5432"))
            >>> 
            >>> prod = base.branch() 
            >>> prod.add(DatabaseConnection("prod-cluster:5432"))
            >>> # Both inherit logger and metrics, but use different databases
        
        Returns:
            Container: A new child container that inherits from this container
            
        Note:
            Child containers share the same registry as their parent, ensuring
            consistent factory and hook behavior across the container hierarchy.
        """
        return Container(registry=self.registry, parent=self)

    def call[**P, R](
        self, func: t.Callable[P, R], /, *args: P.args, **kwargs: P.kwargs
    ) -> R:
        """Calls a function or class with the provided arguments and keyword arguments, injecting dependencies from the
        container. This will create instances of any dependencies that are not already stored in the container or its
        parents.

        Works with both @injectable decorated functions and regular functions (analyzed dynamically).
        For async functions, returns a coroutine that must be awaited.
        """
        if isinstance(func, type):
            return self._call_type(func, args, kwargs)

        injectable = func if isinstance(func, InjectableCallable) else InjectableCallable.from_callable(func)

        if injectable.is_async:
            return injectable.call_using_async(self, *args, **kwargs)
        else:
            return injectable.call_using(self, *args, **kwargs)

    @t.overload
    def get[T: Instance](self, dependency: t.Type[T], *, context: dict[str, Any] | None = None) -> T:
        ...

    @t.overload
    def get[T: Instance, D](self, dependency: t.Type[T], *, default: D, context: dict[str, Any] | None = None) -> T | D:
        ...

    @t.overload
    def get[T: Instance](self, dependency: t.Type[T], *, default_factory: t.Callable[[], T], context: dict[str, Any] | None = None) -> T:
        ...

    @t.overload
    def get[T: Instance, D](self, dependency: t.Type[T], *, default: D, default_factory: t.Callable[[], T], context: dict[str, Any] | None = None) -> T | D:
        ...

    @t.overload
    def get[T: Instance](self, dependency: t.Type[T], *, qualifier: str, context: dict[str, Any] | None = None) -> T:
        ...

    @t.overload
    def get[T: Instance, D](self, dependency: t.Type[T], *, qualifier: str, default: D, context: dict[str, Any] | None = None) -> T | D:
        ...

    @t.overload
    def get[T: Instance](self, dependency: t.Type[T], *, qualifier: str, default_factory: t.Callable[[], T], context: dict[str, Any] | None = None) -> T:
        ...

    @t.overload
    def get[T: Instance, D](self, dependency: t.Type[T], *, qualifier: str, default: D, default_factory: t.Callable[[], T], context: dict[str, Any] | None = None) -> T | D:
        ...

    def get[T: Instance, D](self, dependency: t.Type[T], **kwargs) -> T | D:
        """Gets an instance of the desired dependency from the container. If the dependency is not already stored in the
        container or its parents, a new instance will be created and stored for reuse. When a default is given it will
        be returned instead of creating a new instance, the default is not stored. When a default_factory is given,
        it will be used instead of normal resolution if no instance exists, and the result will be cached using the
        factory as the key. When a qualifier is given, it will look up the qualified instance."""
        return self.find(dependency, **kwargs).get()

    @t.overload
    def find[T: Instance](self, dependency: t.Type[T], *, context: dict[str, Any] | None = None) -> Result[T]:
        ...

    @t.overload
    def find[T: Instance, D](self, dependency: t.Type[T], *, default: D, context: dict[str, Any] | None = None) -> Result[T | D]:
        ...

    @t.overload
    def find[T: Instance](self, dependency: t.Type[T], *, default_factory: t.Callable[[], T], context: dict[str, Any] | None = None) -> Result[T]:
        ...

    @t.overload
    def find[T: Instance, D](self, dependency: t.Type[T], *, default: D, default_factory: t.Callable[[], T], context: dict[str, Any] | None = None) -> Result[T | D]:
        ...

    @t.overload
    def find[T: Instance](self, dependency: t.Type[T], *, qualifier: str, context: dict[str, Any] | None = None) -> Result[T]:
        ...

    @t.overload
    def find[T: Instance, D](self, dependency: t.Type[T], *, qualifier: str, default: D, context: dict[str, Any] | None = None) -> Result[T | D]:
        ...

    @t.overload
    def find[T: Instance](self, dependency: t.Type[T], *, qualifier: str, default_factory: t.Callable[[], T], context: dict[str, Any] | None = None) -> Result[T]:
        ...

    @t.overload
    def find[T: Instance, D](self, dependency: t.Type[T], *, qualifier: str, default: D, default_factory: t.Callable[[], T], context: dict[str, Any] | None = None) -> Result[T | D]:
        ...

    def find[T: Instance, D](self, dependency: t.Type[T], **kwargs) -> Result[T | D]:
        """Returns a Result object for async/sync dependency resolution.

        This method mirrors the get() signature but returns a Result that can be resolved
        in either sync (via .get()) or async (via .get_async() or await) contexts.

        Args:
            dependency: The type to resolve
            **kwargs: Same parameters as get() - default, default_factory, qualifier, context

        Returns:
            Result: A Result object that can be resolved sync or async
        """
        return Result(self, dependency, **kwargs)

    def _build_injection_chain(self, function_name: str, injection_chain: list[str] = None) -> list[str]:
        """Build the injection chain for tracking nested dependency calls."""
        context_chain = _current_injection_chain.get([])
        
        if injection_chain is None and context_chain:
            # We're in a nested call (e.g., from a factory), use context chain
            return context_chain + [function_name]
        elif injection_chain is None:
            # Top-level call
            return [function_name]
        else:
            # Explicit chain provided
            return injection_chain + [function_name]

    async def _inject_single_dependency(
        self, param_name: str, param_type: type, options, injection_config: dict,
        function_name: str, current_injection_chain: list[str], parameter_default
    ) -> Any:
        """Inject a single dependency parameter (async)."""
        # Create injection context for hooks
        injection_context = InjectionContext(
            function_name=function_name,
            parameter_name=param_name,
            requested_type=param_type,
            options=options,
            injection_strategy=injection_config['strategy'],
            type_matching=injection_config['type_matching'],
            strict_mode=injection_config['strict_mode'],
            debug_mode=injection_config['debug_mode'],
            injection_chain=current_injection_chain.copy(),
            parameter_default=parameter_default,
        )

        # Call INJECTION_REQUEST hook - allows hooks to provide the value directly
        hook_result = await self.registry.hooks[Hook.INJECTION_REQUEST].handle(self, injection_context)
        if isinstance(hook_result, Optional.Some):
            # Hook provided a value, use it directly
            return await self._handle_injection_success(hook_result.value, injection_context)

        # Set the context chain for nested factory calls
        token = _current_injection_chain.set(current_injection_chain)
        try:
            injected_value = await self._resolve_dependency_with_hooks(
                param_type, options, injection_context
            )
        except DependencyResolutionError as e:
            return await self._handle_injection_failure(
                e, param_type, param_name, injection_context
            )
        else:
            return await self._handle_injection_success(
                injected_value, injection_context
            )
        finally:
            _current_injection_chain.reset(token)

    async def _handle_injection_failure(
        self, exception: DependencyResolutionError, param_type: type, param_name: str,
        injection_context: InjectionContext
    ) -> Any:
        """Handle failed dependency injection (async)."""
        debug = create_debug_logger(injection_context.debug_mode)

        if injection_context.strict_mode:
            if is_optional_type(param_type):
                debug.optional_dependency_none(param_name)
                return None
            else:
                raise exception
        else:
            # Non-strict mode: inject None for missing dependencies
            debug.non_strict_mode_none(param_name)
            return None

    async def _handle_injection_success(self, injected_value: Any, injection_context: InjectionContext) -> Any:
        """Handle successful dependency injection (async)."""
        debug = create_debug_logger(injection_context.debug_mode)

        debug.injected_parameter(injection_context.parameter_name, injection_context.requested_type, injected_value)

        # Call INJECTION_RESPONSE hook - allows hooks to transform the injected value
        filtered_value = await self.registry.hooks[Hook.INJECTION_RESPONSE].filter(self, injected_value, {"injection_context": injection_context})

        return filtered_value

    async def _resolve_qualified_dependency(self, param_type: type, qualifier: str, injection_context: InjectionContext):
        """
        Resolve a qualified dependency from the container (async).

        Args:
            param_type: Type to resolve
            qualifier: String qualifier to distinguish multiple implementations
            injection_context: Rich context for hooks

        Returns:
            Resolved qualified dependency instance

        Raises:
            DependencyResolutionError: If qualified dependency cannot be resolved
        """
        debug = create_debug_logger(injection_context.debug_mode)
        debug.resolving_qualified(param_type, qualifier)

        # Check for existing qualified instance
        qualified_key = (param_type, qualifier)
        if qualified_key in self.instances:
            return self.instances[qualified_key]

        # Check parent container
        if self._parent:
            try:
                return await self._parent._resolve_qualified_dependency(param_type, qualifier, injection_context)
            except DependencyResolutionError:
                pass  # Continue to raise error below

        # Qualified dependencies must be explicitly registered - don't create new instances
        raise DependencyResolutionError(
            dependency_type=param_type,
            parameter_name=injection_context.parameter_name,
            message=f"Cannot resolve qualified dependency {param_type.__name__} with qualifier '{qualifier}' for parameter '{injection_context.parameter_name}'"
        )


    async def _resolve_dependency_with_hooks(self, param_type, options, injection_context):
        """
        Resolve a dependency using the hook system with rich context (async).

        Args:
            param_type: Type to resolve
            options: Options object with qualifier, etc.
            injection_context: Rich context for hooks

        Returns:
            Resolved dependency instance
        """
        # Extract actual type if optional
        is_optional = is_optional_type(param_type)
        actual_type = get_non_none_type(param_type) if is_optional else param_type

        try:
            return await self._resolve_single_type_with_hooks(actual_type, options, injection_context)
        except DependencyResolutionError:
            if is_optional:
                # Optional dependency not found - return None
                debug = create_debug_logger(injection_context.debug_mode)
                debug.optional_dependency_none(injection_context.parameter_name)
                return None
            else:
                # Required dependency not found - re-raise
                raise

    async def _resolve_single_type_with_hooks(self, param_type, options, injection_context):
        """
        Resolve a single non-optional type using the hook system (async).

        Args:
            param_type: Type to resolve
            options: Options object
            injection_context: Rich context for hooks

        Returns:
            Resolved instance

        Raises:
            Exception if type cannot be resolved
        """
        debug = create_debug_logger(injection_context.debug_mode)
        debug.resolving_dependency(param_type, options)

        # Build kwargs for Result.find() - handle all options together
        find_kwargs = {"context": {"injection_context": injection_context}}

        if options:
            if options.qualifier:
                debug.resolving_qualified(param_type, options.qualifier)
                find_kwargs["qualifier"] = options.qualifier
            if options.default_factory:
                debug.using_default_factory(param_type)
                find_kwargs["default_factory"] = options.default_factory
                find_kwargs["cache_factory_result"] = options.cache_factory_result

        # Delegate ALL resolution to Result.get_async() which handles qualified + default_factory combinations
        try:
            return await self.find(param_type, **find_kwargs).get_async()

        except DependencyResolutionError as e:
            # Re-raise with proper parameter name if it's not already set
            if e.parameter_name == "unknown":
                # Preserve qualified dependency error messages and add parameter context
                error_msg = str(e)
                if "qualified" in error_msg.lower():
                    # Update message to include parameter name
                    if "parameter '" in error_msg:
                        # Message already has parameter info, just replace it
                        updated_msg = error_msg.replace("parameter 'unknown'", f"parameter '{injection_context.parameter_name}'")
                    else:
                        # Add parameter info to the message
                        updated_msg = f"{error_msg} for parameter '{injection_context.parameter_name}'"
                    raise DependencyResolutionError(
                        dependency_type=param_type,
                        parameter_name=injection_context.parameter_name,
                        message=updated_msg
                    ) from e
                else:
                    # Generic dependency error
                    type_name = getattr(param_type, '__name__', str(param_type))
                    raise DependencyResolutionError(
                        dependency_type=param_type,
                        parameter_name=injection_context.parameter_name,
                        message=f"Cannot resolve dependency {type_name} for parameter '{injection_context.parameter_name}'"
                    ) from e
            else:
                # Parameter name already set, just re-raise
                raise
    
    def _create_instance_with_hooks(self, dependency, injection_context):
        """
        Create an instance with hook integration for richer context.
        
        Args:
            dependency: Type to create
            injection_context: Rich context for hooks
            
        Returns:
            Created instance
        """
        # Use container.get() which delegates to Result (async-native)
        return self.get(dependency, context={"injection_context": injection_context})

    def _resolve_dependency(self, param_type, options, type_matching, strict_mode, debug_mode):
        """
        Resolve a single dependency from the container.
        
        Args:
            param_type: Type to resolve
            options: Options object with qualifier, etc.
            type_matching: Type matching strategy
            strict_mode: Whether to raise errors or return None
            debug_mode: Whether to log debug info
            
        Returns:
            Resolved dependency instance
            
        Raises:
            Exception if dependency cannot be resolved and strict_mode is True
        """
        
        actual_type = get_non_none_type(param_type)
        try:
            return self._resolve_single_type(actual_type, options, type_matching, debug_mode)
        except DependencyResolutionError:
            if is_optional_type(param_type):
                # Optional dependency not found
                return None

            raise

    def _resolve_single_type(self, param_type, options, type_matching, debug_mode):
        """
        Resolve a single non-optional type from the container.

        Args:
            param_type: Type to resolve
            options: Options object
            type_matching: Type matching strategy
            debug_mode: Whether to log debug info

        Returns:
            Resolved instance

        Raises:
            Exception if type cannot be resolved
        """
        debug = create_debug_logger(debug_mode)
        debug.resolving_dependency(param_type, options)

        # Handle qualified dependencies
        if options and options.qualifier:
            # Create a dummy injection context for the legacy path
            from bevy.hooks import InjectionContext
            from bevy.injection_types import InjectionStrategy, TypeMatchingStrategy
            injection_context = InjectionContext(
                function_name="legacy_resolution",
                parameter_name="unknown",
                requested_type=param_type,
                options=options,
                injection_strategy=InjectionStrategy.REQUESTED_ONLY,
                type_matching=TypeMatchingStrategy.SUBCLASS,
                strict_mode=True,
                debug_mode=debug_mode,
                injection_chain=[]
            )
            return self._resolve_qualified_dependency(param_type, options.qualifier, injection_context)

        # Delegate ALL resolution to container.get() which uses Result (single source of truth)
        get_kwargs = {}
        if options and options.default_factory:
            debug.using_default_factory(param_type)
            get_kwargs["default_factory"] = options.default_factory
            get_kwargs["cache_factory_result"] = options.cache_factory_result

        return self.get(param_type, **get_kwargs)

    def _call_type[T](self, type_: t.Type[T], args, kwargs) -> T:
        instance = type_.__new__(type_, *args, **kwargs)
        self.call(instance.__init__, *args, **kwargs)
        return instance

    def _get_factory_cache_result(self, factory: t.Callable) -> t.Any | None:
        """
        Get cached result for a factory function, checking parent containers.
        
        Args:
            factory: The factory function to look up
            
        Returns:
            Cached result if found, None otherwise
        """
        if factory in self.instances:
            return self.instances[factory]
        
        if self._parent:
            return self._parent._get_factory_cache_result(factory)
        
        return None

    def _find_factory_for_type(self, dependency):
        if not isinstance(dependency, type):
            return Optional.Nothing()

        for factory_type, factory in self.registry.factories.items():
            if issubclass_or_raises(
                dependency,
                factory_type,
                TypeError(f"Cannot check if {dependency!r} is a subclass of {factory_type!r}")
            ):
                return Optional.Some(factory)

        return Optional.Nothing()

    def _get_existing_instance(self, dependency: t.Type[Instance]) -> Optional[Instance]:
        if dependency in self.instances:
            return Optional.Some(self.instances[dependency])

        if not isinstance(dependency, type):
            return Optional.Nothing()

        for instance_type, instance in self.instances.items():
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


def _unwrap_function(func: object) -> Any:
    if hasattr(func, "__wrapped__"):
        return _unwrap_function(func.__wrapped__)

    if hasattr(func, "__func__"):
        return _unwrap_function(func.__func__)

    return func


@t.overload
def get_container() -> Container:
    ...


@t.overload
def get_container(obj: Container | None) -> Container:
    ...


@t.overload
def get_container(*, using_registry: "registries.Registry") -> Container:
    ...


@t.overload
def get_container(obj: Container | None, *, using_registry: "registries.Registry") -> Container:
    ...


def get_container(*args, **kwargs) -> Container:
    """Gets a container from the global context, a provided container, or a registry.

    With no parameters it returns the global container. Note that this will create a new container if the global context
    does not already have one.

    When given a container it returns that container unless it is None. When it is None it returns the global container.
    Note that this will create a new container if the provided container is None and the global context does not already
    have one.

    A registry can be passed to use in place of the global registry with the using_registry keyword argument. Containers
    created by this registry will not be stored in the global context."""
    match args:
        case (Container() as container,):
            return container

        case () | (None,):
            match kwargs:
                case {"using_registry": registries.Registry() as registry}:
                    return registry.create_container()

                case {}:
                    return get_global_container()

                case _:
                    names = (name for name in kwargs if name not in {"using_registry"})
                    raise NameError(
                        f"Invalid keyword name(s): {', '.join(names)}"
                    )

        case _:
            raise ValueError(f"Invalid positional arguments: {args}\nExpected no parameters, a Container, or None.")
