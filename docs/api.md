# API Reference

## Core Decorators

### @injectable

Decorator that enables dependency injection for functions. Functions with `Inject[T]` parameters must use this decorator or be called via `Container.call()`.

```python
from bevy import injectable, Inject

@injectable
def process_data(service: Inject[UserService], data: str):
    return service.process(data)
```

**Parameters:**
- `strategy: InjectionStrategy` - Controls which parameters are injected (default: `REQUESTED_ONLY`)
- `params: list[str]` - Specific parameter names to inject (used with `ONLY` strategy)
- `strict: bool` - Whether to raise errors for missing dependencies (default: `True`)
- `debug: bool` - Enable debug logging (default: `False`)
- `type_matching: TypeMatchingStrategy` - How to match types (default: `SUBCLASS`)
- `cache_analysis: bool` - Cache function signature analysis (default: `True`)

**Usage Examples:**

```python
# Basic usage
@injectable
def basic_function(service: Inject[UserService]):
    pass

# With options
@injectable(strategy=InjectionStrategy.ANY_NOT_PASSED, debug=True)
def configured_function(service: UserService, data: str):
    pass

# Specific parameters only
@injectable(strategy=InjectionStrategy.ONLY, params=["service"])
def selective_function(service: UserService, manual: str):
    pass
```

### @auto_inject

Decorator that automatically uses the global container for dependency injection. Must be combined with `@injectable`.

```python
from bevy import auto_inject, injectable, Inject

@auto_inject
@injectable
def global_function(service: Inject[UserService]):
    return service.process()

# Call directly - no container needed
result = global_function()
```

**Important:** `@auto_inject` must come before `@injectable` in the decorator chain.

## Type System

### Inject[T]

Type alias for declaring injectable parameters. Preserves IDE type hints and autocomplete.

```python
from bevy import Inject

# Basic injection
def func(service: Inject[UserService]): pass

# With options
def func(service: Inject[UserService, Options(qualifier="primary")]): pass

# Optional dependency
def func(service: Inject[UserService | None]): pass
```

### Options

Configuration class for dependency behavior.

```python
from bevy import Options

class Options:
    def __init__(
        self,
        qualifier: str | None = None,
        from_config: str | None = None, 
        default_factory: Callable[[], Any] | None = None
    ):
        pass
```

**Parameters:**
- `qualifier: str` - Named qualifier for multiple instances of same type
- `from_config: str` - Configuration key to bind dependency from
- `default_factory: Callable` - Factory function to use when dependency not found

**Usage Examples:**

```python
# Qualified dependencies
@injectable 
def func(
    primary_db: Inject[Database, Options(qualifier="primary")],
    backup_db: Inject[Database, Options(qualifier="backup")]
):
    pass

# Configuration binding
@injectable
def func(config: Inject[dict, Options(from_config="app.settings")]):
    pass

# Default factory
@injectable
def func(
    logger: Inject[Logger, Options(default_factory=lambda: Logger("default"))]
):
    pass
```

## Enums

### InjectionStrategy

Controls which function parameters are eligible for injection.

```python
from bevy import InjectionStrategy

class InjectionStrategy(Enum):
    REQUESTED_ONLY = "requested_only"  # Only Inject[T] parameters (default)
    ANY_NOT_PASSED = "any_not_passed"  # Any typed parameter not provided
    ONLY = "only"                      # Only specific parameters (requires params list)
```

**Examples:**

```python
# Default - only inject Inject[T] parameters
@injectable
def explicit(service: Inject[UserService], manual: str): pass

# Inject any typed parameter not provided at call time
@injectable(strategy=InjectionStrategy.ANY_NOT_PASSED)
def auto(service: UserService, data: str): pass

# Only inject specific parameters
@injectable(strategy=InjectionStrategy.ONLY, params=["service"])
def selective(service: UserService, manual: str): pass
```

### TypeMatchingStrategy

Controls how types are matched during dependency resolution.

```python
from bevy import TypeMatchingStrategy

class TypeMatchingStrategy(Enum):
    EXACT_TYPE = "exact_type"    # Exact type match only
    SUBCLASS = "subclass"        # Allow subclasses (default)
```

## Container and Registry

### Container

Manages dependency instances and handles injection.

```python
from bevy import Container, Registry

class Container:
    def __init__(self, registry: Registry, *, parent: Container | None = None):
        """Create a new container.
        
        Args:
            registry: Registry with factories and hooks
            parent: Parent container for inheritance (optional)
        """
        
    def add(self, instance: Any) -> None:
        """Add instance using its type as key."""
        
    def add(self, for_dependency: type, instance: Any) -> None:
        """Add instance for specific type."""
        
    def get[T](self, dependency: type[T]) -> T:
        """Get instance of dependency type, creating if needed."""
        
    def get[T](self, dependency: type[T], *, default: Any) -> T | Any:
        """Get instance with default fallback."""
        
    def call[**P, R](self, func: Callable[P, R], /, *args: P.args, **kwargs: P.kwargs) -> R:
        """Call function with dependency injection."""
        
    def branch(self) -> Container:
        """Create child container that inherits from this one."""
```

**Usage Examples:**

```python
# Create container
registry = Registry()
container = Container(registry)

# Add instances
container.add(UserService())
container.add(Database, ProductionDatabase())

# Get instances
service = container.get(UserService)
db = container.get(Database, default=None)

# Call functions with injection
@injectable
def process(service: Inject[UserService], data: str):
    return service.process(data)

result = container.call(process, data="test")

# Container branching
child = container.branch()
child.add(Database, TestDatabase())  # Override for testing
```

### Registry

Stores factories and hooks for dependency creation.

```python
from bevy import Registry

class Registry:
    def __init__(self):
        """Create new registry."""
        
    def add_factory(self, factory: Callable, dependency_type: type | None = None):
        """Add factory for dependency type."""
        
    def add_hook(self, hook_type: Hook, callback: Callable):
        """Add hook callback."""
        
    def create_container(self) -> Container:
        """Create container using this registry."""
```

## Global Functions

### get_container

Get or create global container.

```python
from bevy import get_container

def get_container() -> Container:
    """Get global container, creating if needed."""

def get_container(obj: Container | None) -> Container:
    """Get provided container or global if None."""

def get_container(*, using_registry: Registry) -> Container:
    """Create container with specific registry."""
```

### get_registry

Get or create global registry.

```python
from bevy import get_registry

def get_registry() -> Registry:
    """Get global registry, creating if needed."""

def get_registry(obj: Registry | None) -> Registry:
    """Get provided registry or global if None."""
```

## Type Utilities

### Type Inspection Functions

Utilities for working with injection types.

```python
from bevy.injection_types import (
    extract_injection_info,
    is_optional_type,
    get_non_none_type
)

def extract_injection_info(annotation: type) -> tuple[type, Options | None]:
    """Extract type and options from Inject[T] or Inject[T, Options] annotation."""

def is_optional_type(annotation: type) -> bool:
    """Check if type is optional (T | None)."""

def get_non_none_type(annotation: type) -> type:
    """Get the non-None type from T | None union."""
```

**Examples:**

```python
# Extract injection info
def func(service: Inject[UserService, Options(qualifier="test")]): pass

annotation = func.__annotations__['service']
actual_type, options = extract_injection_info(annotation)
# actual_type = UserService
# options.qualifier = "test"

# Optional type checking
def func(service: UserService | None): pass

annotation = func.__annotations__['service']
is_optional = is_optional_type(annotation)  # True
actual_type = get_non_none_type(annotation)  # UserService
```

## Hooks System

### Hook Types

Available hook types for extending behavior.

```python
from bevy.hooks import Hook

class Hook(Enum):
    # Core instance hooks
    GET_INSTANCE = "get_instance"
    GOT_INSTANCE = "got_instance" 
    CREATE_INSTANCE = "create_instance"
    CREATED_INSTANCE = "created_instance"
    HANDLE_UNSUPPORTED_DEPENDENCY = "handle_unsupported_dependency"
    
    # Injection-specific hooks
    INJECTION_REQUEST = "injection_request"
    INJECTION_RESPONSE = "injection_response"
    POST_INJECTION_CALL = "post_injection_call"
    FACTORY_MISSING_TYPE = "factory_missing_type"
    MISSING_INJECTABLE = "missing_injectable"
```

### Hook Decorators

Convenient decorators for registering hooks.

```python
from bevy.hooks import hooks

@hooks.INJECTION_REQUEST
def log_injection_request(container, context):
    print(f"Injecting {context.requested_type}")

@hooks.POST_INJECTION_CALL
def log_execution_time(container, context):
    print(f"Executed in {context.execution_time_ms}ms")

# Register with registry
registry = get_registry()
log_injection_request.register_hook(registry)
log_execution_time.register_hook(registry)
```

### Hook Context Classes

Rich context objects provided to hooks.

```python
from bevy.hooks import InjectionContext, PostInjectionContext

@dataclass
class InjectionContext:
    function_name: str
    parameter_name: str
    requested_type: type
    options: Options | None
    injection_strategy: InjectionStrategy
    type_matching: TypeMatchingStrategy
    strict_mode: bool
    debug_mode: bool
    injection_chain: list[str]

@dataclass  
class PostInjectionContext:
    function_name: str
    injected_params: dict[str, Any]
    result: Any
    injection_strategy: InjectionStrategy
    debug_mode: bool
    execution_time_ms: float
```

## Bundled Utilities

### Type Factory Hook

Automatic type creation hook for simple dependency management.

```python
from bevy.bundled.type_factory_hook import type_factory

# Register with registry to enable automatic type creation
registry = get_registry()
type_factory.register_hook(registry)

# Now any class can be automatically created
@injectable
def func(service: Inject[UserService]):  # UserService() created automatically
    pass
```

## Error Handling

### Strict vs Non-Strict Mode

Control error handling behavior for missing dependencies.

```python
# Strict mode (default) - raises errors
@injectable(strict=True)
def strict_func(service: Inject[MissingService]):
    pass  # Raises exception if MissingService not found

# Non-strict mode - injects None
@injectable(strict=False)
def lenient_func(service: Inject[MissingService]):
    if service is None:
        # Handle missing dependency gracefully
        pass
```

### Optional Dependencies

Use union types for optional dependencies.

```python
@injectable
def handle_optional(
    required: Inject[UserService],           # Must be available
    optional: Inject[CacheService | None]    # Can be None
):
    if optional:
        # Use optional service
        pass
```

## Configuration

### Debug Mode

Enable detailed logging for troubleshooting.

```python
@injectable(debug=True)
def debug_function(service: Inject[UserService]):
    pass

# Output:
# [BEVY DEBUG] Resolving <class 'UserService'> with options None
# [BEVY DEBUG] Injected service: <class 'UserService'> = <UserService object at 0x...>
```

### Context Variables

Control global context behavior.

```python
import os

# Disable global context (testing)
os.environ["BEVY_ENABLE_GLOBAL_CONTEXT"] = "False"

# This will raise GlobalContextDisabledError
container = get_container()  # Error!
```

## Migration from Bevy 2.x

### API Changes

| Bevy 2.x | Bevy 3.x |
|----------|----------|
| `@inject` | `@injectable` or `@auto_inject` + `@injectable` |
| `dependency()` | `Inject[T]` |
| `dependency(factory)` | `Inject[T, Options(default_factory=factory)]` |
| Default parameters | Type annotations only |

### Example Migration

```python
# OLD (2.x)
@inject
def old_function(
    service: UserService = dependency(),
    db: Database = dependency(custom_factory)
):
    pass

# NEW (3.x)
@auto_inject
@injectable
def new_function(
    service: Inject[UserService],
    db: Inject[Database, Options(default_factory=custom_factory)]
):
    pass
```

## Best Practices

1. **Type Hints**: Always use proper type annotations with `Inject[T]`
2. **IDE Support**: The new system preserves full IDE autocomplete and type checking
3. **Container Management**: Use container branching for test isolation
4. **Hook Registration**: Register `type_factory` hook for convenience
5. **Optional Dependencies**: Use `T | None` for non-critical dependencies
6. **Debug Mode**: Enable during development for troubleshooting
7. **Error Handling**: Use strict mode in production, non-strict for graceful degradation