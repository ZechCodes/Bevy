# Bevy
Bevy makes using *Dependency Injection* in *Python* a breeze so that you can focus on creating amazing code.

## Installation
```shell script
pip install bevy>3.0.0
```

## Dependency Injection
Put simply, *Dependency Injection* is a design pattern where the objects that your code depends on are instantiated by the caller. Those dependencies are then injected into your code when it is run.
This promotes loosely coupled code where your code doesn't require direct knowledge of what objects it depends on or how to create them. Instead, your code declares what interface it expects and an outside framework handles the work of creating objects with the correct interface.

## Interfaces
Python doesn't have an actual interface implementation like many other languages. Class inheritance, however, can be used in a very similar way since subclasses will likely have the same fundamental interface as their base class. 

## Why Do I Care?
*Dependency Injection* and its reliance on abstract interfaces makes your code easier to maintain:
- Changes can be made without needing to alter implementation details in unrelated code, so long as the interface isn't modified in a substantial way.
- Tests can provide mock implementations of dependencies without needing to rely on patching or duck typing. They can provide the mock to Bevy which can then ensure it is used when necessary.

## How It Works
Bevy uses Python 3.12+ type annotations with `Inject[T]` to declare dependencies, and decorators like `@injectable` and `@auto_inject` to enable dependency injection. The type system preserves IDE autocomplete and type checking while providing powerful dependency management.

### Basic Usage

**Declaring Dependencies**
```python
from bevy import injectable, Inject

class DatabaseService:
    def query(self, sql: str):
        return f"Executing: {sql}"

class UserService:
    def __init__(self):
        pass
    
    def get_user(self, user_id: str):
        return f"User {user_id}"

@injectable
def process_user_data(
    user_service: Inject[UserService],
    db_service: Inject[DatabaseService],
    user_id: str
):
    user = user_service.get_user(user_id)
    result = db_service.query(f"SELECT * FROM users WHERE id = {user_id}")
    return f"Processed {user} with {result}"
```

**Using with Container**
```python
from bevy import Container, Registry

# Create container with services
registry = Registry()
container = Container(registry)
container.add(UserService())
container.add(DatabaseService())

# Call function with dependency injection
result = container.call(process_user_data, user_id="123")
print(result)  # "Processed User 123 with Executing: SELECT * FROM users WHERE id = 123"
```

**Global Container with @auto_inject**
```python
from bevy import auto_inject, injectable, Inject, get_container

# Set up global container
container = get_container()
container.add(UserService())
container.add(DatabaseService())

@auto_inject
@injectable  
def process_user_data(
    user_service: Inject[UserService],
    db_service: Inject[DatabaseService], 
    user_id: str
):
    user = user_service.get_user(user_id)
    result = db_service.query(f"SELECT * FROM users WHERE id = {user_id}")
    return f"Processed {user} with {result}"

# Call directly - dependencies injected automatically
result = process_user_data(user_id="456")
```

### Advanced Features

**Optional Dependencies**
```python
@injectable
def handle_request(
    user_service: Inject[UserService],
    cache_service: Inject[CacheService | None],  # Optional dependency
    request_id: str
):
    user = user_service.get_user(request_id)
    
    if cache_service:
        cached_data = cache_service.get(request_id)
        return f"Cached: {cached_data}"
    else:
        return f"No cache available for {user}"
```

**Dependency Options**
```python
from bevy import Options

@injectable
def advanced_processing(
    primary_db: Inject[DatabaseService, Options(qualifier="primary")],
    backup_db: Inject[DatabaseService, Options(qualifier="backup")], 
    logger: Inject[Logger, Options(default_factory=lambda: Logger("default"))],
    data: str
):
    # Use qualified dependencies and default factories
    pass
```

**Injection Strategies**
```python
from bevy import InjectionStrategy

# Only inject parameters explicitly marked with Inject[T]
@injectable(strategy=InjectionStrategy.REQUESTED_ONLY)  # Default
def explicit_injection(service: Inject[UserService], manual_param: str):
    pass

# Inject any parameter not provided at call time
@injectable(strategy=InjectionStrategy.ANY_NOT_PASSED)
def auto_injection(service: UserService, db: DatabaseService, manual_param: str):
    pass

# Only inject specific parameters
@injectable(strategy=InjectionStrategy.ONLY, params=["service"])
def selective_injection(service: UserService, db: DatabaseService, manual_param: str):
    pass
```

**Configuration Options**
```python
@injectable(
    strategy=InjectionStrategy.REQUESTED_ONLY,
    strict=True,      # Raise errors for missing dependencies (default)
    debug=True,       # Enable debug logging
    type_matching=TypeMatchingStrategy.SUBCLASS  # Allow subclass matching
)
def configured_function(service: Inject[UserService]):
    pass
```

## Container Management

**Creating and Using Containers**
```python
from bevy import Registry, Container

# Create registry and container
registry = Registry()
container = Container(registry)

# Add instances
container.add(UserService())
container.add(DatabaseService, DatabaseService("production"))

# Create branched containers for isolation
test_container = container.branch()
test_container.add(DatabaseService("test"))  # Override for testing

# Get instances directly
user_service = container.get(UserService)
```

**Global Container**
```python
from bevy import get_container, get_registry

# Get global container (creates if needed)
container = get_container()

# Work with global registry
registry = get_registry()
registry.add_factory(some_factory)
```

## Type System

The type system provides full IDE support while enabling powerful dependency features:

- `Inject[T]` - Basic dependency injection
- `Inject[T, Options(...)]` - Dependency with configuration  
- `Inject[T | None]` - Optional dependency
- `Options(qualifier="name")` - Qualified dependencies
- `Options(default_factory=lambda: T())` - Default factory

## Hooks and Extensibility

Bevy provides a rich hook system for customization:

```python
from bevy.hooks import hooks, Hook

@hooks.INJECTION_REQUEST
def log_injection_request(container, context):
    print(f"Injecting {context.requested_type} for {context.function_name}")

@hooks.POST_INJECTION_CALL  
def log_execution_time(container, context):
    print(f"Function {context.function_name} took {context.execution_time_ms}ms")

# Register hooks with registry
registry = get_registry()
log_injection_request.register_hook(registry)
log_execution_time.register_hook(registry)
```

## Error Handling

Bevy provides clear error messages and flexible error handling:

```python
# Strict mode (default) - raises errors for missing dependencies
@injectable(strict=True)
def strict_function(service: Inject[MissingService]):
    pass

# Non-strict mode - injects None for missing dependencies  
@injectable(strict=False)
def lenient_function(service: Inject[MissingService]):
    if service is None:
        # Handle missing dependency gracefully
        pass
```

## Best Practices

1. **Use type hints**: Always provide proper type annotations for dependencies
2. **Prefer composition**: Design services that depend on interfaces rather than concrete implementations
3. **Use containers for testing**: Create isolated test containers with mock dependencies
4. **Leverage optional dependencies**: Use `T | None` for optional services
5. **Configure appropriately**: Use strict mode in production, debug mode during development

## CLI Documentation Tool

Bevy includes a built-in CLI tool for exploring documentation:

```bash
# Show docstring and file location
python -m bevy bevy.containers.Container

# Show function/class signature
python -m bevy bevy.containers.Container.get signature

# List module or class members
python -m bevy bevy.containers members
```

**Features:**
- Shows docstrings and source file locations
- Displays function signatures with proper formatting
- Shows class inheritance and `__init__` signatures
- Supports overloaded functions (Python 3.11+)
- Lists all members of modules and classes

**Examples:**
```bash
# View Container class documentation
python -m bevy bevy.containers.Container

# See the signature of the get method
python -m bevy bevy.containers.Container.get signature

# List all members of the bevy module
python -m bevy bevy members

# Works with built-in modules too
python -m bevy os.path.join signature
```

## Migration from Earlier Versions

If you're upgrading from Bevy 3.0 beta, see our [Migration Guide](docs/migration.md) for step-by-step instructions on updating your code.