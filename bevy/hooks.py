import functools
import inspect
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Optional as OptionalType, TYPE_CHECKING

from tramp.optionals import Optional

import bevy.registries as r

if TYPE_CHECKING:
    from bevy.containers import Container
    from bevy.injection_types import Options, InjectionStrategy, TypeMatchingStrategy

type HookFunction[T] = "Callable[[Container, Type[T], dict[str, Any], T]"


def _call_hook_with_appropriate_signature(hook_func: Callable, container: "Container", value: Any, context: dict[str, Any], _from_wrapper: bool = False) -> Any:
    """Call a hook function with the appropriate number of parameters based on its signature.
    
    Supports both legacy 2-parameter hooks (container, value) and new 3-parameter hooks 
    (container, value, context) for backwards compatibility.
    """
    # If this is a HookWrapper and we're not being called from the wrapper itself
    if isinstance(hook_func, HookWrapper) and not _from_wrapper:
        # Let the wrapper handle the call
        return hook_func(container, value, context)
    
    # Get the actual function for signature inspection
    func = hook_func.func if hasattr(hook_func, 'func') else hook_func
    
    # Get function signature
    try:
        sig = inspect.signature(func)
    except (ValueError, TypeError):
        # If we can't inspect, assume new style with context
        return func(container, value, context)
    else:
        params = list(sig.parameters.keys())

        # Check if the function expects 3 parameters (container, value, context)
        # or 2 parameters (container, value) for backwards compatibility
        if len(params) >= 3:
            # New style with context
            return func(container, value, context)
        else:
            # Legacy style without context
            return func(container, value)



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
    parameter_default: Optional[Any]  # Optional.Some(value) if default set, Optional.Nothing() if unset
    
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
    
    # Injection-specific hooks
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

    def handle[T](self, container: "Container", value: T, context: dict[str, Any] | None = None) -> Optional[Any]:
        """Iterates each callback and returns the first result."""
        ctx = context or {}
        for callback in self.callbacks:
            match _call_hook_with_appropriate_signature(callback, container, value, ctx):
                case Optional.Some() as v:
                    return v

        return Optional.Nothing()

    def filter[T](self, container: "Container", value: T, context: dict[str, Any] | None = None) -> T:
        """Iterates all callbacks and updates the value when a callback returns a Some result."""
        ctx = context or {}
        for callback in self.callbacks:
            match _call_hook_with_appropriate_signature(callback, container, value, ctx):
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

    def __call__(self, container: "Container", value: P, context=None) -> Optional[R]:
        # Use the shared helper to call with appropriate signature, marking we're from wrapper
        return _call_hook_with_appropriate_signature(self.func, container, value, context or {}, _from_wrapper=True)

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
    
    # Injection-specific hook decorators
    INJECTION_REQUEST = _HookDecoratorDescriptor()
    INJECTION_RESPONSE = _HookDecoratorDescriptor()
    POST_INJECTION_CALL = _HookDecoratorDescriptor()
    FACTORY_MISSING_TYPE = _HookDecoratorDescriptor()
    MISSING_INJECTABLE = _HookDecoratorDescriptor()

    def __init__(self, hook_type: Hook):
        self.hook_type = hook_type

    def __call__(self, func: Callable[P, R]) -> HookWrapper[P, R]:
        return HookWrapper(self.hook_type, func)

    def __repr__(self):
        return f"HookDecorator({self.hook_type})"


hooks = HookDecorator
