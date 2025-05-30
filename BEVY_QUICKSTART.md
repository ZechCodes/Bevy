# Bevy Quick Start Guide

**Bevy** is a Python dependency injection framework that makes managing dependencies simple and elegant. Get up and running in minutes with this quick start guide.

## Installation

```bash
pip install bevy>=3.0.0
```

## Core Concepts

### What is Dependency Injection?
Dependency injection is a design pattern where objects your code depends on are created and provided by an external framework, rather than being created directly in your code. This makes your code more modular, testable, and maintainable.

### Key Components
- **Registry**: Stores factories and hooks for creating dependencies
- **Container**: Manages instances of dependencies and handles injection
- **Dependencies**: Objects that are automatically created and injected
- **Factories**: Functions that define how to create specific types
- **Hooks**: Extension points for customizing dependency creation and lifecycle

### Important Rules
- Functions using `dependency()` must be decorated with `@inject` OR called via `Container.call()`
- By default, containers have no handlers - you must register factories or hooks to create instances
- `dependency()` can optionally take a factory function that receives a container and returns an instance

## Basic Usage

### 1. Simple Function Injection

```python
from bevy import inject, dependency, get_registry
from bevy.factories import create_type_factory


# Define your classes
class Database:
    def __init__(self):
        self.connection = "Connected to DB"


class UserService:
    @inject  # Required when using dependency() in __init__
    def __init__(self, db: Database = dependency()):
        self.db = db

    def get_user(self, user_id: int):
        return f"User {user_id} from {self.db.connection}"


# Register factories so the container knows how to create instances
registry = get_registry()
registry.add_factory(create_type_factory(Database))
registry.add_factory(create_type_factory(UserService))


# Use dependency injection
@inject
def get_user_data(user_id: int, service: UserService = dependency()):
    return service.get_user(user_id)


# Call the function - dependencies are automatically injected
result = get_user_data(123)
print(result)  # "User 123 from Connected to DB"
```

### 2. Container.call() Method

```python
from bevy import get_registry, get_container
from bevy.factories import create_type_factory

class ApiClient:
    def __init__(self):
        self.base_url = "https://api.example.com"

class DataProcessor:
    def __init__(self, api: ApiClient = dependency()):
        self.api = api
    
    def process_data(self):
        return f"Processing data from {self.api.base_url}"

# Register factory
registry = get_registry()
registry.add_factory(create_type_factory(ApiClient))

# Use container.call() instead of @inject decorator
container = get_container()
processor = container.call(DataProcessor)
result = processor.process_data()
```

### 3. Custom Factories

```python
from bevy import inject, dependency, get_registry
from bevy.factories import create_type_factory

class Config:
    def __init__(self, env: str = "production"):
        self.env = env
        self.debug = env == "development"

# Register a custom factory with parameters
registry = get_registry()
registry.add_factory(create_type_factory(Config, "development"))

@inject
def app_startup(config: Config = dependency()):
    print(f"Starting app in {config.env} mode, debug={config.debug}")

app_startup()  # "Starting app in development mode, debug=True"
```

### 4. Using Type Factory Hook for Auto-Creation

```python
from bevy import inject, dependency, get_registry
from bevy.bundled.type_factory_hook import type_factory

class Logger:
    def __init__(self, name: str = "app"):
        self.name = name

# Register the type factory hook to auto-create any class
registry = get_registry()
type_factory.register_hook(registry)

@inject
def log_message(logger: Logger = dependency()):
    return f"[{logger.name}] Hello World"

# No explicit factory needed - type_factory hook handles it
result = log_message()  # "[app] Hello World"
```

### 5. Dependency Factory Functions

```python
from bevy import inject, dependency

class ApiClient:
    def __init__(self, timeout: int = 10):
        self.timeout = timeout

# Factory function that creates configured instances
def create_api_client(container):
    return ApiClient(timeout=30)

@inject
def process_api_data(client: ApiClient = dependency(create_api_client)):
    return f"Processing with timeout: {client.timeout}"

result = process_api_data()  # "Processing with timeout: 30"
```

### 6. Manual Container Management

```python
from bevy.registries import Registry
from bevy.factories import create_type_factory

class Database:
    def __init__(self):
        self.connection = "Connected to DB"

# Create a custom registry and container
registry = Registry()
registry.add_factory(create_type_factory(Database))

container = registry.create_container()

# Get dependencies manually
db = container.get(Database)
print(db.connection)  # "Connected to DB"
```

### 7. Container Branching & Isolation

```python
from bevy.registries import Registry
from bevy.factories import create_type_factory

class Logger:
    def __init__(self, level: str = "INFO"):
        self.level = level

class Database:
    def __init__(self, url: str = "sqlite://"):
        self.url = url

# Create parent container
registry = Registry()
registry.add_factory(create_type_factory(Logger, "DEBUG"))

parent_container = registry.create_container()
parent_logger = parent_container.get(Logger)
print(f"Parent logger level: {parent_logger.level}")  # "DEBUG"

# Create child container that inherits from parent
child_container = parent_container.branch()

# Child gets same instance from parent
child_logger = child_container.get(Logger)
assert child_logger is parent_logger  # True

# But child maintains separate instance cache for new types
registry.add_factory(create_type_factory(Database, "postgres://localhost"))
child_database = child_container.get(Database)
parent_database = parent_container.get(Database)
print(f"Same database instance: {parent_database is child_database}")  # False
```

### 8. Context Managers for Scoped Dependencies

```python
from bevy.registries import Registry
from bevy.factories import create_type_factory

class Database:
    def __init__(self):
        self.connection = "Connected to DB"

# Use registry as context manager for scoped dependencies
with Registry() as registry:
    registry.add_factory(create_type_factory(Database))
    
    with registry.create_container() as container:
        # Dependencies created within this scope
        db = container.get(Database)
        print(db.connection)  # "Connected to DB"
        # Container automatically manages lifecycle
```

## Advanced Features

### Hooks for Lifecycle Management

Hooks can be decorated functions that are easily registered:

```python
from bevy.registries import Registry
from bevy.hooks import hooks
from bevy.factories import create_type_factory
from tramp.optionals import Optional

class Service:
    def __init__(self, name: str = "default"):
        self.name = name

@hooks.CREATED_INSTANCE
def log_instance_creation(container, instance):
    """This hook runs after any instance is created"""
    print(f"Created instance: {type(instance).__name__}")
    return instance

@hooks.GET_INSTANCE  
def custom_service_provider(container, dependency_type):
    """This hook runs before getting any instance"""
    if dependency_type is Service:
        return Optional.Some(Service("custom"))
    return Optional.Nothing()

# Register hooks
registry = Registry()
log_instance_creation.register_hook(registry)
custom_service_provider.register_hook(registry)

# Use the hooks
container = registry.create_container()
service = container.get(Service)  # Uses custom provider, logs creation
print(service.name)  # "custom"
```

### Hook Types Available

- `hooks.GET_INSTANCE`: Intercept before getting/creating an instance
- `hooks.GOT_INSTANCE`: Filter/modify an instance after it's retrieved
- `hooks.CREATE_INSTANCE`: Intercept before creating a new instance  
- `hooks.CREATED_INSTANCE`: Filter/modify an instance after it's created
- `hooks.HANDLE_UNSUPPORTED_DEPENDENCY`: Handle types with no registered factory

## Best Practices

1. **Always use @inject or container.call()**: Functions with `dependency()` parameters require one of these
2. **Register factories or use type_factory hook**: Containers need to know how to create instances
3. **Use type hints**: Always specify type hints for dependency parameters
4. **Keep factories simple**: Factories should focus on object creation, not business logic
5. **Test with mocks**: Use dependency injection to easily substitute test doubles
6. **Scope appropriately**: Use container branching to isolate dependencies when needed

## Common Patterns

### Repository Pattern with Interface
```python
from abc import ABC, abstractmethod
from bevy import inject, dependency, get_registry
from bevy.factories import create_type_factory

class UserRepository(ABC):
    @abstractmethod
    def get_user(self, user_id: int): pass

class Database:
    def query(self, sql: str):
        return f"Query result: {sql}"

class DatabaseUserRepository(UserRepository):
    @inject
    def __init__(self, db: Database = dependency()):
        self.db = db
    
    def get_user(self, user_id: int):
        return self.db.query(f"SELECT * FROM users WHERE id = {user_id}")

# Register factories for both the interface and concrete implementation
registry = get_registry()
registry.add_factory(create_type_factory(Database))
registry.add_factory(create_type_factory(DatabaseUserRepository), UserRepository)

@inject
def get_user_service(repo: UserRepository = dependency()):
    return repo.get_user(123)
```

### Configuration Injection
```python
import os
from bevy import inject, dependency, get_registry
from bevy.factories import create_type_factory

class AppConfig:
    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL", "sqlite:///app.db")
        self.api_key = os.getenv("API_KEY")

registry = get_registry()
registry.add_factory(create_type_factory(AppConfig))

@inject
def initialize_app(config: AppConfig = dependency()):
    print(f"Connecting to {config.database_url}")
    return f"App initialized with {config.database_url}"
```

## Migration from Other DI Frameworks

Bevy's approach is designed to be intuitive and Pythonic. If you're coming from other frameworks:

- **From dependency-injector**: Replace `@inject` providers with `dependency()` defaults
- **From Flask-Injector**: Use `@inject` decorator instead of automatic injection
- **From Django**: Replace Django's implicit dependency resolution with explicit `dependency()` declarations

## Troubleshooting

- **Missing dependencies**: Ensure type hints are specified and match registered types
- **Circular dependencies**: Use factory functions to defer creation
- **Global context issues**: Check `BEVY_ENABLE_GLOBAL_CONTEXT` environment variable
- **Type errors**: Verify that dependency types are properly imported in the namespace

---

**That's it!** You now have everything needed to start using Bevy for dependency injection in your Python applications. The framework handles the complexity while keeping your code clean and testable.