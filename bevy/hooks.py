import functools
from enum import Enum
from dataclasses import dataclass
from tramp.optionals import Optional
from typing import Any, Callable, TYPE_CHECKING, Optional as OptionalType

import bevy.registries as r

if TYPE_CHECKING:
    from bevy.containers import Container
    from bevy.injection_types import Options, InjectionStrategy, TypeMatchingStrategy

type HookFunction[T] = "Callable[[Container, Type[T]], T]"


@dataclass
class InjectionContext:
    """Rich context information provided to injection hooks."""
    function_name: str
    parameter_name: str
    requested_type: type
    options: OptionalType["Options"]
    injection_strategy: "InjectionStrategy"
    type_matching: "TypeMatchingStrategy"
    strict_mode: bool
    debug_mode: bool
    injection_chain: list[str]  # Stack of function calls leading to this injection
    
    def __post_init__(self):
        """Ensure injection_chain is a list."""
        if self.injection_chain is None:
            self.injection_chain = []


@dataclass  
class PostInjectionContext:
    """Context for post-injection hooks after function call completion."""
    function_name: str
    injected_params: dict[str, Any]  # Map of parameter names to injected values
    result: Any
    injection_strategy: "InjectionStrategy"
    debug_mode: bool
    execution_time_ms: float


class Hook(Enum):
    GET_INSTANCE = "get_instance"
    GOT_INSTANCE = "got_instance"
    CREATE_INSTANCE = "create_instance"
    CREATED_INSTANCE = "created_instance"
    HANDLE_UNSUPPORTED_DEPENDENCY = "handle_unsupported_dependency"
    
    # New injection-specific hooks
    INJECTION_REQUEST = "injection_request"      # Before resolving a dependency for injection
    INJECTION_RESPONSE = "injection_response"    # After resolving a dependency for injection
    POST_INJECTION_CALL = "post_injection_call"  # After calling function with injected dependencies
    FACTORY_MISSING_TYPE = "factory_missing_type"  # When no factory found for a type
    MISSING_INJECTABLE = "missing_injectable"    # When dependency cannot be resolved


class HookManager:
    """A utility type that makes it easier to work with collections of functions waiting for the
    hook to be triggered."""
    def __init__(self):
        self.callbacks = set()

    def add_callback(self, hook: HookFunction):
        """Adds a function that will be called when the hook is triggered."""
        self.callbacks.add(hook)

    def handle[T](self, container: "Container", value: T) -> Optional[Any]:
        """Iterates each callback and returns the first result."""
        for callback in self.callbacks:
            match callback(container, value):
                case Optional.Some() as v:
                    return v

        return Optional.Nothing()

    def filter[T](self, container: "Container", value: T) -> T:
        """Iterates all callbacks and updates the value when a callback returns a Some result."""
        for callback in self.callbacks:
            match callback(container, value):
                case Optional.Some(v):
                    value = v
                case Optional.Nothing():
                    pass

        return value


class HookWrapper[**P, R]:
    """Wraps a hook callback function to make it easier to register with a registry."""
    __match_args__ = ("hook_type",)

    def __init__(self, hook_type: Hook, func: Callable[P, R]):
        self.hook_type = hook_type
        self.func = func

        functools.update_wrapper(self, func)

    def __call__(self, container: "Container", value: P) -> Optional[R]:
        return self.func(container, value)

    def register_hook(self, registry: "r.Registry | None" = None):
        """Adds the callback to a registry for the hook type."""
        registry = r.get_registry(registry)
        registry.add_hook(self)


class _HookDecoratorDescriptor:
    def __init__(self):
        self.hook_type: Optional[Hook] = Optional.Nothing()

    def __get__(self, instance, owner):
        match self.hook_type:
            case Optional.Some(hook_type):
                return HookDecorator(hook_type)

            case Optional.Nothing():
                raise ValueError("Hook type is not yet set. Accessed before owning class definition fully created.")

            case _:
                raise ValueError("Invalid value for hook type.")

    def __set_name__(self, owner, name):
        self.hook_type = Optional.Some(Hook[name])


class HookDecorator[**P, R]:
    """A decorator that wraps a function in a hook type to simplifying adding to a registry. This class is aliased as
    "hooks" for convenience. It provides decorators for each hook type for even simpler syntax.

    Example:
        @hooks.GET_INSTANCE
        def foobar(container: Container, some_thing: Thing) -> Thing:
            ...
    """
    GET_INSTANCE = _HookDecoratorDescriptor()
    GOT_INSTANCE = _HookDecoratorDescriptor()
    CREATE_INSTANCE = _HookDecoratorDescriptor()
    CREATED_INSTANCE = _HookDecoratorDescriptor()
    HANDLE_UNSUPPORTED_DEPENDENCY = _HookDecoratorDescriptor()
    
    # New injection-specific hook decorators
    INJECTION_REQUEST = _HookDecoratorDescriptor()
    INJECTION_RESPONSE = _HookDecoratorDescriptor()
    POST_INJECTION_CALL = _HookDecoratorDescriptor()
    FACTORY_MISSING_TYPE = _HookDecoratorDescriptor()
    MISSING_INJECTABLE = _HookDecoratorDescriptor()

    def __init__(self, hook_type: Hook):
        self.hook_type = hook_type

    def __call__(self, func: Callable[P, R]) -> HookWrapper[P, R]:
        return HookWrapper(self.hook_type, func)


hooks = HookDecorator
