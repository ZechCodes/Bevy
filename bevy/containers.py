import time
import typing as t
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
    InjectionStrategy, TypeMatchingStrategy,
    extract_injection_info, is_optional_type, get_non_none_type
)
from bevy.injections import get_injection_info, analyze_function_signature

type Instance = t.Any


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
                return self._call_function(func, args, kwargs)

    def _call_function[**P, R](self, func: t.Callable[P, R], args: P.args, kwargs: P.kwargs) -> R:
        start_time = time.time()
        
        # Get function signature 
        sig = signature(func)
        function_name = getattr(func, '__name__', str(func))
        
        # Check if function has injection metadata from @injectable decorator
        injection_info = get_injection_info(func)
        
        if injection_info:
            # Use metadata from @injectable decorator
            injection_params = injection_info['params']
            injection_strategy = injection_info['strategy']
            type_matching = injection_info['type_matching']
            strict_mode = injection_info['strict_mode']
            debug_mode = injection_info['debug_mode']
        else:
            # Analyze function dynamically using ANY_NOT_PASSED strategy
            injection_params = analyze_function_signature(func, InjectionStrategy.ANY_NOT_PASSED)
            injection_strategy = InjectionStrategy.ANY_NOT_PASSED
            type_matching = TypeMatchingStrategy.SUBCLASS
            strict_mode = True
            debug_mode = False
        
        # Bind provided arguments
        bound_args = sig.bind_partial(*args, **kwargs)
        bound_args.apply_defaults()
        
        # Track injected parameters for hooks
        injected_params = {}
        
        # Inject missing dependencies
        for param_name, (param_type, options) in injection_params.items():
            if param_name not in bound_args.arguments:
                # Create injection context for hooks
                injection_context = InjectionContext(
                    function_name=function_name,
                    parameter_name=param_name,
                    requested_type=param_type,
                    options=options,
                    injection_strategy=injection_strategy,
                    type_matching=type_matching,
                    strict_mode=strict_mode,
                    debug_mode=debug_mode,
                    injection_chain=[function_name]  # TODO: Track full call stack
                )
                
                # Call INJECTION_REQUEST hook
                self.registry.hooks[Hook.INJECTION_REQUEST].handle(self, injection_context)
                
                # This parameter needs injection
                try:
                    injected_value = self._resolve_dependency_with_hooks(
                        param_type, options, injection_context
                    )
                    bound_args.arguments[param_name] = injected_value
                    injected_params[param_name] = injected_value
                    
                    # Call INJECTION_RESPONSE hook
                    injection_context.result = injected_value  # Add result to context
                    self.registry.hooks[Hook.INJECTION_RESPONSE].handle(self, injection_context)
                    
                    if debug_mode:
                        print(f"[BEVY DEBUG] Injected {param_name}: {param_type} = {injected_value}")
                        
                except Exception as e:
                    if strict_mode:
                        # Check if this is an optional type
                        if is_optional_type(param_type):
                            bound_args.arguments[param_name] = None
                            injected_params[param_name] = None
                            if debug_mode:
                                print(f"[BEVY DEBUG] Optional dependency {param_name} not found, using None")
                        else:
                            # Call MISSING_INJECTABLE hook before raising
                            self.registry.hooks[Hook.MISSING_INJECTABLE].handle(self, injection_context)
                            raise
                    else:
                        # Non-strict mode: inject None for missing dependencies
                        bound_args.arguments[param_name] = None
                        injected_params[param_name] = None
                        if debug_mode:
                            print(f"[BEVY DEBUG] Non-strict mode: {param_name} not found, using None")
        
        # Call function with resolved arguments
        result = func(*bound_args.args, **bound_args.kwargs)
        
        # Call POST_INJECTION_CALL hook
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
        
        return result

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
            except Exception:
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
            
        except Exception as e:
            # Call FACTORY_MISSING_TYPE hook if no factory found
            self.registry.hooks[Hook.FACTORY_MISSING_TYPE].handle(self, injection_context)
            raise e
    
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
                raise TypeError(f"No handler found that can handle dependency: {dependency!r}")

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
