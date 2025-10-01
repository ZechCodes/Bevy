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
        default_factory: Callable[[], Any] | None = None,
        cache_factory_result: bool = True
    ):
        pass
```

**Parameters:**
- `qualifier: str` - Named qualifier for multiple instances of same type  
- `default_factory: Callable` - Factory function to use when dependency not found
- `cache_factory_result: bool` - Whether to cache factory results (default: True)

**Usage Examples:**

```python
# Qualified dependencies
@injectable 
def func(
    primary_db: Inject[Database, Options(qualifier="primary")],
    backup_db: Inject[Database, Options(qualifier="backup")]
):
    pass

# Default factory
@injectable
def func(
    logger: Inject[Logger, Options(default_factory=lambda: Logger("default"))]
):
    pass

# Factory caching control
@injectable  
def test_func(
    # Cached factory result (default behavior)
    db: Inject[Database, Options(default_factory=create_db)],
    # Fresh instance each call (testing scenarios)
    test_db: Inject[Database, Options(
        default_factory=create_test_db, 
        cache_factory_result=False
    )]
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
        
    def add(self, for_dependency: type, instance: Any, *, qualifier: str) -> None:
        """Add qualified instance for specific type."""
        
    def get[T](self, dependency: type[T]) -> T:
        """Get instance of dependency type, creating if needed."""
        
    def get[T](self, dependency: type[T], *, default: Any) -> T | Any:
        """Get instance with default fallback."""

    def find[T](self, dependency: type[T]) -> Result[T]:
        """Get Result for async/sync dependency resolution."""

    def find[T](self, dependency: type[T], *, qualifier: str) -> Result[T]:
        """Get Result for qualified dependency."""

    def find[T](self, dependency: type[T], *, default_factory: Callable[[], T]) -> Result[T]:
        """Get Result with default factory."""

    def call[**P, R](self, func: Callable[P, R], /, *args: P.args, **kwargs: P.kwargs) -> R:
        """Call function with dependency injection.

        For async functions, returns a coroutine that must be awaited.
        """

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

# Add qualified instances
container.add(Database, primary_db, qualifier="primary")
container.add(Database, backup_db, qualifier="backup")

# Get instances (sync)
service = container.get(UserService)
db = container.get(Database, default=None)

# Get instances (async)
service = await container.find(UserService)
primary_db = await container.find(Database, qualifier="primary")
config = await container.find(Config, default_factory=load_config)

# Call functions with injection (sync)
@injectable
def process(service: Inject[UserService], data: str):
    return service.process(data)

result = container.call(process, data="test")

# Call functions with injection (async)
@injectable
async def process_async(service: Inject[UserService], data: str):
    return await service.process_async(data)

result = await container.call(process_async, data="test")

# Container branching
child = container.branch()
child.add(Database, TestDatabase())  # Override for testing
```

### Result[T]

Represents a deferred dependency resolution that can be executed in either sync or async contexts.

```python
from bevy.find_results import Result

class Result[T]:
    def get(self) -> T:
        """Resolve dependency synchronously.

        Runs async resolution in a thread with an isolated event loop.
        Use this only when you cannot use async/await.
        """

    async def get_async(self) -> T:
        """Resolve dependency asynchronously.

        Truly async-native resolution with no thread overhead.
        Async hooks execute in the same async context.
        """

    def __await__(self):
        """Allow direct awaiting: instance = await result"""
```

**Usage Examples:**

```python
# In async code - recommended
async def process_order():
    db = await container.find(Database)  # Truly async
    cache = await container.find(Cache)

    # Or equivalently
    result = container.find(Database)
    db = await result.get_async()

# In sync code
def sync_process():
    db = container.find(Database).get()  # Runs async in thread
    # Or just use get() directly
    db = container.get(Database)

# All options work with find()
result = container.find(
    Database,
    qualifier="primary",
    default_factory=create_db,
)
db = await result  # Direct await
```

**Why use `find()` over `get()` in async code?**

- `container.get(T)` spawns a thread + event loop for async hooks
- `await container.find(T)` stays truly async with no thread overhead
- Async hooks can do real async work (I/O, delays) when using `find()`
- Dependencies injected into async functions use `find()` automatically

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

## Factory Caching

### Default Factory Caching

Default factories are cached by factory function to optimize performance while maintaining semantic correctness.

```python
def create_expensive_db():
    print("Creating expensive database connection...")
    return Database("expensive://connection")

@injectable
def service_a(db: Inject[Database, Options(default_factory=create_expensive_db)]):
    return f"Service A: {db.url}"

@injectable 
def service_b(db: Inject[Database, Options(default_factory=create_expensive_db)]):
    return f"Service B: {db.url}"

# Factory is called only once - same instance shared
container.call(service_a)  # "Creating expensive database connection..."
container.call(service_b)  # No factory call - reuses cached instance
```

### Caching Control

Control factory caching behavior with `cache_factory_result`:

```python
# Cached (default) - same factory = same instance
@injectable
def cached_service(
    db: Inject[Database, Options(default_factory=create_db)]
):
    pass

# Uncached - fresh instance each time
@injectable
def fresh_service(
    db: Inject[Database, Options(
        default_factory=create_test_db,
        cache_factory_result=False
    )]
):
    pass
```

### Factory Isolation

Different factory functions create isolated instances:

```python
def create_prod_db():
    return Database("postgresql://prod")

def create_test_db():
    return Database("sqlite://test")

@injectable
def prod_service(db: Inject[Database, Options(default_factory=create_prod_db)]):
    pass  # Gets production database

@injectable
def test_service(db: Inject[Database, Options(default_factory=create_test_db)]):
    pass  # Gets test database (different instance)
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

## Migration from Bevy 3.0 Beta

### API Changes

| Bevy 3.0 Beta | Bevy 3.1 Beta |
|---------------|---------------|
| `@inject` | `@injectable` or `@auto_inject` + `@injectable` |
| `dependency()` | `Inject[T]` |
| `dependency(factory)` | `Inject[T, Options(default_factory=factory)]` |
| Default parameters | Type annotations only |

### Example Migration

```python
# OLD (3.0 beta)
@inject
def old_function(
    service: UserService = dependency(),
    db: Database = dependency(custom_factory)
):
    pass

# Current (3.1 beta)
@auto_inject
@injectable
def process_user(
    service: Inject[UserService],
    db: Inject[Database, Options(default_factory=custom_factory)]
):
    pass
```

## Best Practices

1. **Type Hints**: Always use proper type annotations with `Inject[T]`
2. **IDE Support**: The system preserves full IDE autocomplete and type checking
3. **Container Management**: Use container branching for test isolation
4. **Hook Registration**: Register `type_factory` hook for convenience
5. **Optional Dependencies**: Use `T | None` for non-critical dependencies
6. **Debug Mode**: Enable during development for troubleshooting
7. **Error Handling**: Use strict mode in production, non-strict for graceful degradation