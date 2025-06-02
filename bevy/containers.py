import time
import typing as t
from contextvars import ContextVar
from inspect import get_annotations, signature
from types import MethodType
from typing import Any

from tramp.optionals import Optional

import bevy.injections as injections
import bevy.registries as registries
from bevy.context_vars import GlobalContextMixin, get_global_container, global_container
# DependencyMetadata removed - using injection system
from bevy.hooks import Hook, InjectionContext, PostInjectionContext
from bevy.injection_types import (
    InjectionStrategy, TypeMatchingStrategy, DependencyResolutionError,
    extract_injection_info, is_optional_type, get_non_none_type
)
from bevy.injections import get_injection_info, analyze_function_signature

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

    Containers can be branched to isolate dependencies while still sharing the same registry and preexisting instances."""
    def __init__(self, registry: "registries.Registry", *, parent: "Container | None" = None):
        super().__init__()
        self.registry = registry
        self.instances: dict[t.Type[Instance], Instance] = {
            Container: self,
            registries.Registry: registry,
        }
        self._parent = parent

    @t.overload
    def add(self, instance: Instance):
        ...

    @t.overload
    def add(self, for_dependency: t.Type[Instance], instance: Instance):
        ...

    def add(self, *args):
        match args:
            case [instance]:
                self.instances[type(instance)] = instance

            case [for_dependency, instance]:
                self.instances[for_dependency] = instance

            case _:
                raise ValueError(f"Unexpected arguments to add: {args}")

    def branch(self) -> "Container":
        """Creates a branch off of the current container, isolating dependencies from the parent container. Dependencies
        existing on the parent container will be shared with the branched container."""
        return Container(registry=self.registry, parent=self)

    def call[**P, R](
        self, func: t.Callable[P, R], /, *args: P.args, **kwargs: P.kwargs
    ) -> R:
        """Calls a function or class with the provided arguments and keyword arguments, injecting dependencies from the
        container. This will create instances of any dependencies that are not already stored in the container or its
        parents. 
        
        Works with both @injectable decorated functions and regular functions (analyzed dynamically).
        """
        return self._call(func, args, kwargs)

    @t.overload
    def get[T: Instance](self, dependency: t.Type[T]) -> T:
        ...

    @t.overload
    def get[T: Instance, D](self, dependency: t.Type[T], *, default: D) -> T | D:
        ...

    def get[T: Instance, D](self, dependency: t.Type[T], **kwargs) -> T | D:
        """Gets an instance of the desired dependency from the container. If the dependency is not already stored in the
        container or its parents, a new instance will be created and stored for reuse. When a default is given it will
        be returned instead of creating a new instance, the default is not stored."""
        using_default = False
        match self.registry.hooks[Hook.GET_INSTANCE].handle(self, dependency):
            case Optional.Some(v):
                instance = v

            case Optional.Nothing():
                if dep := self._get_existing_instance(dependency):
                    instance = dep.value
                else:
                    dep = None
                    if self._parent:
                        dep = self._parent.get(dependency, default=None)

                    if dep is None:
                        if "default" in kwargs:
                            dep = kwargs["default"]
                            using_default = True
                        else:
                            dep = self._create_instance(dependency)

                    instance = dep

            case _:
                raise ValueError(f"Invalid value for dependency: {dependency}, must be an Optional type.")

        instance = self.registry.hooks[Hook.GOT_INSTANCE].filter(self, instance)
        if not using_default:
            self.instances[dependency] = instance

        return instance

    def _call[**P, R](self, func: t.Callable[P, R] | t.Type[R], args: P.args, kwargs: P.kwargs) -> R:
        match func:
            case type():
                return self._call_type(func, args, kwargs)

            case _:
                return self._call_function(func, args, kwargs, injection_chain=None)

    def _call_function[**P, R](self, func: t.Callable[P, R], args: P.args, kwargs: P.kwargs, injection_chain: list[str] = None) -> R:
        start_time = time.time()
        
        # Prepare function metadata and injection context
        function_name = getattr(func, '__name__', str(func))
        current_injection_chain = self._build_injection_chain(function_name, injection_chain)
        injection_config = self._get_injection_configuration(func)
        
        # Bind provided arguments
        sig = signature(func)
        bound_args = sig.bind_partial(*args, **kwargs)
        bound_args.apply_defaults()
        
        # Inject missing dependencies
        injected_params = self._inject_missing_dependencies(
            injection_config, bound_args, function_name, current_injection_chain
        )
        
        # Call function with resolved arguments
        result = func(*bound_args.args, **bound_args.kwargs)
        
        # Call post-execution hook
        self._call_post_injection_hook(
            function_name, injected_params, result, 
            injection_config['strategy'], injection_config['debug_mode'], 
            start_time
        )
        
        return result

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

    def _get_injection_configuration(self, func) -> dict:
        """Get injection configuration from function metadata or defaults."""
        injection_info = get_injection_info(func)
        
        if injection_info:
            # Use metadata from @injectable decorator
            return {
                'params': injection_info['params'],
                'strategy': injection_info['strategy'],
                'type_matching': injection_info['type_matching'],
                'strict_mode': injection_info['strict_mode'],
                'debug_mode': injection_info['debug_mode']
            }
        else:
            # Analyze function dynamically using ANY_NOT_PASSED strategy
            return {
                'params': analyze_function_signature(func, InjectionStrategy.ANY_NOT_PASSED),
                'strategy': InjectionStrategy.ANY_NOT_PASSED,
                'type_matching': TypeMatchingStrategy.SUBCLASS,
                'strict_mode': True,
                'debug_mode': False
            }

    def _inject_missing_dependencies(
        self, injection_config: dict, bound_args, function_name: str, current_injection_chain: list[str]
    ) -> dict[str, Any]:
        """Inject missing dependencies into bound arguments."""
        injected_params = {}
        
        for param_name, (param_type, options) in injection_config['params'].items():
            if param_name not in bound_args.arguments:
                injected_value = self._inject_single_dependency(
                    param_name, param_type, options, injection_config, 
                    function_name, current_injection_chain
                )
                bound_args.arguments[param_name] = injected_value
                injected_params[param_name] = injected_value
        
        return injected_params

    def _inject_single_dependency(
        self, param_name: str, param_type: type, options, injection_config: dict,
        function_name: str, current_injection_chain: list[str]
    ) -> Any:
        """Inject a single dependency parameter."""
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
            injection_chain=current_injection_chain.copy()
        )
        
        # Call INJECTION_REQUEST hook
        self.registry.hooks[Hook.INJECTION_REQUEST].handle(self, injection_context)
        
        # Set the context chain for nested factory calls
        token = _current_injection_chain.set(current_injection_chain)
        try:
            injected_value = self._resolve_dependency_with_hooks(
                param_type, options, injection_context
            )
        except DependencyResolutionError as e:
            return self._handle_injection_failure(
                e, param_type, param_name, injection_context
            )
        else:
            return self._handle_injection_success(
                injected_value, injection_context
            )
        finally:
            _current_injection_chain.reset(token)

    def _handle_injection_failure(
        self, exception: DependencyResolutionError, param_type: type, param_name: str, 
        injection_context: InjectionContext
    ) -> Any:
        """Handle failed dependency injection."""
        if injection_context.strict_mode:
            if is_optional_type(param_type):
                if injection_context.debug_mode:
                    print(f"[BEVY DEBUG] Optional dependency {param_name} not found, using None")
                return None
            else:
                # Call MISSING_INJECTABLE hook before raising
                self.registry.hooks[Hook.MISSING_INJECTABLE].handle(self, injection_context)
                raise exception
        else:
            # Non-strict mode: inject None for missing dependencies
            if injection_context.debug_mode:
                print(f"[BEVY DEBUG] Non-strict mode: {param_name} not found, using None")
            return None

    def _handle_injection_success(self, injected_value: Any, injection_context: InjectionContext) -> Any:
        """Handle successful dependency injection."""
        # Call INJECTION_RESPONSE hook
        injection_context.result = injected_value  # Add result to context
        self.registry.hooks[Hook.INJECTION_RESPONSE].handle(self, injection_context)
        
        if injection_context.debug_mode:
            print(f"[BEVY DEBUG] Injected {injection_context.parameter_name}: {injection_context.requested_type} = {injected_value}")
        
        return injected_value

    def _call_post_injection_hook(
        self, function_name: str, injected_params: dict, result: Any,
        injection_strategy: InjectionStrategy, debug_mode: bool, start_time: float
    ):
        """Call the post-injection hook with execution context."""
        execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        post_context = PostInjectionContext(
            function_name=function_name,
            injected_params=injected_params,
            result=result,
            injection_strategy=injection_strategy,
            debug_mode=debug_mode,
            execution_time_ms=execution_time
        )
        self.registry.hooks[Hook.POST_INJECTION_CALL].handle(self, post_context)

    def _resolve_dependency_with_hooks(self, param_type, options, injection_context):
        """
        Resolve a dependency using the hook system with rich context.
        
        Args:
            param_type: Type to resolve
            options: Options object with qualifier, etc.
            injection_context: Rich context for hooks
            
        Returns:
            Resolved dependency instance
        """
        
        # Handle optional types (Type | None)
        if is_optional_type(param_type):
            actual_type = get_non_none_type(param_type)
            try:
                return self._resolve_single_type_with_hooks(actual_type, options, injection_context)
            except DependencyResolutionError:
                # Optional dependency not found
                if injection_context.debug_mode:
                    print(f"[BEVY DEBUG] Optional dependency {injection_context.parameter_name} not found, using None")
                return None
        else:
            return self._resolve_single_type_with_hooks(param_type, options, injection_context)
    
    def _resolve_single_type_with_hooks(self, param_type, options, injection_context):
        """
        Resolve a single non-optional type using the hook system.
        
        Args:
            param_type: Type to resolve
            options: Options object
            injection_context: Rich context for hooks
            
        Returns:
            Resolved instance
            
        Raises:
            Exception if type cannot be resolved
        """
        if injection_context.debug_mode:
            print(f"[BEVY DEBUG] Resolving {param_type} with options {options}")
        
        # Handle qualified dependencies
        if options and options.qualifier:
            raise NotImplementedError(
                f"Qualified dependencies not yet implemented. "
                f"Cannot resolve {param_type} with qualifier '{options.qualifier}'. "
                f"This feature will be added in a future update."
            )
        
        # Handle configuration binding
        if options and options.from_config:
            raise NotImplementedError(
                f"Configuration binding not yet implemented. "
                f"Cannot resolve {param_type} from config key '{options.from_config}'. "
                f"This feature will be added in a future update."
            )
        
        # Handle default factory - use it instead of normal resolution
        if options and options.default_factory:
            if injection_context.debug_mode:
                print(f"[BEVY DEBUG] Using default factory for {param_type}")
            return options.default_factory()
        
        # Try to resolve from container - check for existing instance first
        try:
            # Check if instance already exists
            if existing := self._get_existing_instance(param_type):
                return existing.value
            
            # Try to create new instance
            return self._create_instance_with_hooks(param_type, injection_context)
            
        except DependencyResolutionError as e:
            # Call FACTORY_MISSING_TYPE hook if no factory found
            self.registry.hooks[Hook.FACTORY_MISSING_TYPE].handle(self, injection_context)
            # Re-raise with proper parameter name if it's not already set
            if e.parameter_name == "unknown":
                raise DependencyResolutionError(
                    dependency_type=param_type,
                    parameter_name=injection_context.parameter_name,
                    message=f"Cannot resolve dependency {param_type.__name__} for parameter '{injection_context.parameter_name}'"
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
        # Use existing create_instance logic but with hook integration
        match self.registry.hooks[Hook.CREATE_INSTANCE].handle(self, dependency):
            case Optional.Some(v):
                instance = v

            case Optional.Nothing():
                match self._find_factory_for_type(dependency):
                    case Optional.Some(factory):
                        instance = factory(self)

                    case Optional.Nothing():
                        instance = self._handle_unsupported_dependency(dependency)

                    case _:
                        raise RuntimeError(f"Impossible state reached.")

            case _:
                raise ValueError(
                    f"Invalid value returned from hook for dependency: {dependency}, must be a {Optional.__qualname__}."
                )

        # Store the instance and apply created instance hooks
        filtered_instance = self.registry.hooks[Hook.CREATED_INSTANCE].filter(self, instance)
        self.instances[dependency] = filtered_instance
        
        return filtered_instance

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
        
        # Handle optional types (Type | None)
        if is_optional_type(param_type):
            actual_type = get_non_none_type(param_type)
            try:
                return self._resolve_single_type(actual_type, options, type_matching, debug_mode)
            except Exception:
                # Optional dependency not found
                return None
        else:
            return self._resolve_single_type(param_type, options, type_matching, debug_mode)

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
        if debug_mode:
            print(f"[BEVY DEBUG] Resolving {param_type} with options {options}")
        
        # Handle qualified dependencies
        if options and options.qualifier:
            raise NotImplementedError(
                f"Qualified dependencies not yet implemented. "
                f"Cannot resolve {param_type} with qualifier '{options.qualifier}'. "
                f"This feature will be added in a future update."
            )
        
        # Handle configuration binding
        if options and options.from_config:
            raise NotImplementedError(
                f"Configuration binding not yet implemented. "
                f"Cannot resolve {param_type} from config key '{options.from_config}'. "
                f"This feature will be added in a future update."
            )
        
        # Handle default factory
        if options and options.default_factory:
            try:
                return self.get(param_type)
            except Exception:
                if debug_mode:
                    print(f"[BEVY DEBUG] Using default factory for {param_type}")
                return options.default_factory()
        
        # Standard resolution using container.get()
        return self.get(param_type)

    def _call_type[T](self, type_: t.Type[T], args, kwargs) -> T:
        instance = type_.__new__(type_, *args, **kwargs)
        self.call(instance.__init__, *args, **kwargs)
        return instance

    def _create_instance(self, dependency: t.Type[Instance]) -> Instance:
        match self.registry.hooks[Hook.CREATE_INSTANCE].handle(self, dependency):
            case Optional.Some(v):
                instance = v

            case Optional.Nothing():
                match self._find_factory_for_type(dependency):
                    case Optional.Some(factory):
                        instance = factory(self)

                    case Optional.Nothing():
                        instance = self._handle_unsupported_dependency(dependency)

                    case _:
                        raise RuntimeError(f"Impossible state reached.")

            case _:
                raise ValueError(
                    f"Invalid value returned from hook for dependency: {dependency}, must be a {Optional.__qualname__}."
                )

        return self.registry.hooks[Hook.CREATED_INSTANCE].filter(self, instance)

    def _handle_unsupported_dependency(self, dependency):
        match self.registry.hooks[Hook.HANDLE_UNSUPPORTED_DEPENDENCY].handle(self, dependency):
            case Optional.Some(v):
                return v

            case Optional.Nothing():
                raise DependencyResolutionError(
                    dependency_type=dependency, 
                    parameter_name="unknown",  # Will be overridden by caller
                    message=f"No handler found that can handle dependency: {dependency!r}"
                )

            case _:
                raise ValueError(
                    f"Invalid value returned from hook for dependency: {dependency}, must be a "
                    f"{Optional.__qualname__}."
                )

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
