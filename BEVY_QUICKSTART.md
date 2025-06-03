# Bevy Quick Start Guide

**Bevy** is a Python dependency injection framework that makes managing dependencies simple and elegant. Get up and running in minutes with this quick start guide.

## Installation

```bash
pip install bevy>=3.1.0
```

## Core Concepts

### What is Dependency Injection?
Dependency injection is a design pattern where objects your code depends on are created and provided by an external framework, rather than being created directly in your code. This makes your code more modular, testable, and maintainable.

### Key Components
- **Registry**: Stores factories and hooks for creating dependencies
- **Container**: Manages instances of dependencies and handles injection
- **@injectable**: Decorator that enables dependency injection for functions
- **@auto_inject**: Decorator that automatically uses the global container
- **Inject[T]**: Type annotation that declares a parameter as injectable
- **Options**: Configuration for dependency behavior (qualifiers, defaults, etc.)

### Important Rules
- Functions using `Inject[T]` must be decorated with `@injectable` OR called via `Container.call()`
- Use `@auto_inject` + `@injectable` for automatic global container injection
- Always use proper type hints with `Inject[T]` for IDE support
- By default, containers have no handlers - register the `type_factory` hook or custom factories

## Basic Usage

### 1. Simple Function Injection with Container

```python
from bevy import injectable, Inject, Container, Registry
from bevy.bundled.type_factory_hook import type_factory

# Define your classes
class Database:
    def __init__(self):
        self.connection = "Connected to DB"

class UserService:
    def __init__(self, db: Database):
        self.db = db

    def get_user(self, user_id: int):
        return f"User {user_id} from {self.db.connection}"

# Set up container with type factory for auto-creation
registry = Registry()
type_factory.register_hook(registry)  # Enables automatic type creation

container = Container(registry)

# Use dependency injection
@injectable
def get_user_data(user_id: int, service: Inject[UserService]):
    return service.get_user(user_id)

# Call the function - dependencies are automatically injected
result = container.call(get_user_data, user_id=123)
print(result)  # "User 123 from Connected to DB"
```

### 2. Global Container with @auto_inject

```python
from bevy import injectable, auto_inject, Inject, get_container
from bevy.bundled.type_factory_hook import type_factory

class ApiClient:
    def __init__(self):
        self.base_url = "https://api.example.com"

class DataProcessor:
    def __init__(self, api: ApiClient):
        self.api = api
    
    def process_data(self):
        return f"Processing data from {self.api.base_url}"

# Set up global container
container = get_container()
type_factory.register_hook(container.registry)

# Use @auto_inject for automatic global injection
@auto_inject
@injectable
def process_api_data(processor: Inject[DataProcessor]):
    return processor.process_data()

# Call directly - no need to use container.call()
result = process_api_data()
print(result)  # "Processing data from https://api.example.com"
```

### 3. Optional Dependencies

```python
from bevy import injectable, Inject, Container, Registry
from bevy.bundled.type_factory_hook import type_factory

class CacheService:
    def get(self, key: str):
        return f"cached_{key}"

class UserService:
    def get_user(self, user_id: str):
        return f"User {user_id}"

# Set up container with only UserService (no CacheService)
registry = Registry()
type_factory.register_hook(registry)
container = Container(registry)
container.add(UserService())  # Add UserService, but not CacheService

@injectable
def handle_request(
    user_service: Inject[UserService],
    cache_service: Inject[CacheService | None],  # Optional dependency
    request_id: str
):
    user = user_service.get_user(request_id)
    
    if cache_service:
        cached_data = cache_service.get(request_id)
        return f"Cached: {cached_data} for {user}"
    else:
        return f"No cache available for {user}"

result = container.call(handle_request, request_id="123")
print(result)  # "No cache available for User 123"
```

### 4. Dependency Options and Default Factories

```python
from bevy import injectable, Inject, Options, Container, Registry

class Logger:
    def __init__(self, name: str = "app"):
        self.name = name
    
    def log(self, message: str):
        return f"[{self.name}] {message}"

class Database:
    def __init__(self, url: str = "sqlite://"):
        self.url = url

def create_expensive_db():
    print("Creating expensive database connection...")
    return Database("postgres://localhost")

registry = Registry()
container = Container(registry)

@injectable
def app_startup(
    # Use default factory when dependency not found
    logger: Inject[Logger, Options(default_factory=lambda: Logger("startup"))],
    # Cached factory result (default behavior)
    db: Inject[Database, Options(default_factory=create_expensive_db)],
):
    logger.log(f"Starting app with database: {db.url}")
    return f"App started with {logger.name} logger and {db.url}"

@injectable
def database_backup(
    # Same factory - reuses cached instance (no factory call)
    db: Inject[Database, Options(default_factory=create_expensive_db)],
):
    return f"Backing up {db.url}"

# First call creates instance
result1 = container.call(app_startup)
print(result1)  # "Creating expensive database connection..."
                # "App started with startup logger and postgres://localhost"

# Second call reuses cached instance
result2 = container.call(database_backup)
print(result2)  # "Backing up postgres://localhost" (no factory call)
```

### 4a. Factory Caching Control

```python
from bevy import injectable, Inject, Options, Container, Registry

def create_test_db():
    print("Creating test database...")
    return Database("sqlite://test.db")

registry = Registry()
container = Container(registry)

@injectable
def test_setup(
    # Fresh instance each call (testing scenarios)
    db: Inject[Database, Options(
        default_factory=create_test_db,
        cache_factory_result=False
    )],
):
    return f"Test with {db.url}"

# Each call creates fresh instance
result1 = container.call(test_setup)  # "Creating test database..."
result2 = container.call(test_setup)  # "Creating test database..." (called again)
print(f"Fresh instances: {result1}, {result2}")
```

### 5. Injection Strategies

```python
from bevy import injectable, Inject, InjectionStrategy, Container, Registry
from bevy.bundled.type_factory_hook import type_factory

class UserService:
    def __init__(self):
        self.name = "UserService"

class DatabaseService:
    def __init__(self):
        self.name = "DatabaseService"

registry = Registry()
type_factory.register_hook(registry)
container = Container(registry)

# Strategy 1: REQUESTED_ONLY (default) - only inject Inject[T] parameters
@injectable
def explicit_injection(
    user_service: Inject[UserService],  # Will be injected
    manual_param: str                   # Must be provided manually
):
    return f"Explicit: {user_service.name}, {manual_param}"

# Strategy 2: ANY_NOT_PASSED - inject any typed parameter not provided
@injectable(strategy=InjectionStrategy.ANY_NOT_PASSED)
def auto_injection(
    user_service: UserService,    # Will be injected if not provided
    db_service: DatabaseService,  # Will be injected if not provided
    manual_param: str             # Will be injected if not provided AND has type
):
    return f"Auto: {user_service.name}, {db_service.name}, {manual_param}"

# Strategy 3: ONLY - inject only specific parameters
@injectable(strategy=InjectionStrategy.ONLY, params=["user_service"])
def selective_injection(
    user_service: UserService,    # Will be injected (in params list)
    db_service: DatabaseService,  # Will NOT be injected
    manual_param: str             # Will NOT be injected
):
    return f"Selective: {user_service.name}, {db_service.name}, {manual_param}"

# Test different strategies
result1 = container.call(explicit_injection, manual_param="test")
print(result1)  # "Explicit: UserService, test"

result2 = container.call(auto_injection, manual_param="test")  
print(result2)  # "Auto: UserService, DatabaseService, test"

result3 = container.call(selective_injection, 
                        db_service=DatabaseService(), 
                        manual_param="test")
print(result3)  # "Selective: UserService, DatabaseService, test"
```

### 6. Container Branching & Isolation

```python
from bevy import Container, Registry
from bevy.bundled.type_factory_hook import type_factory

class Logger:
    def __init__(self, level: str = "INFO"):
        self.level = level

class Database:
    def __init__(self, url: str = "sqlite://"):
        self.url = url

# Create parent container
registry = Registry()
type_factory.register_hook(registry)

parent_container = Container(registry)
parent_container.add(Logger("DEBUG"))

parent_logger = parent_container.get(Logger)
print(f"Parent logger level: {parent_logger.level}")  # "DEBUG"

# Create child container that inherits from parent
child_container = parent_container.branch()

# Child gets same instance from parent
child_logger = child_container.get(Logger)
assert child_logger is parent_logger  # True

# But child maintains separate instance cache for new types
child_database = child_container.get(Database)
parent_database = parent_container.get(Database)
print(f"Same database instance: {parent_database is child_database}")  # False
```

### 7. Configuration and Debug Mode

```python
from bevy import injectable, auto_inject, Inject, TypeMatchingStrategy, get_container
from bevy.bundled.type_factory_hook import type_factory

class Service:
    def __init__(self):
        self.name = "Service"

# Set up global container
container = get_container()
type_factory.register_hook(container.registry)

@auto_inject
@injectable(
    strategy=InjectionStrategy.REQUESTED_ONLY,
    strict=True,        # Raise errors for missing dependencies (default)
    debug=True,         # Enable debug logging
    type_matching=TypeMatchingStrategy.SUBCLASS  # Allow subclass matching
)
def configured_function(service: Inject[Service], message: str):
    return f"Configured: {service.name} - {message}"

# Debug output will show injection details
result = configured_function(message="Hello")
# [BEVY DEBUG] Resolving <class '__main__.Service'> with options None
# [BEVY DEBUG] Injected service: <class '__main__.Service'> = <__main__.Service object at 0x...>
print(result)  # "Configured: Service - Hello"
```

## Advanced Features

### Qualifiers - Managing Multiple Instances of the Same Type

Qualifiers allow you to distinguish between different instances of the same type using string identifiers. This is essential when you need multiple configurations of the same service (e.g., primary/backup databases, different loggers, etc.).

#### Basic Qualifier Usage

```python
from bevy import injectable, Inject, Options, Container, Registry

class Database:
    def __init__(self, name: str, url: str):
        self.name = name
        self.url = url

# Set up container with qualified dependencies
registry = Registry()
container = Container(registry)

# Add multiple Database instances with different qualifiers
primary_db = Database("Primary", "postgresql://primary:5432/app")
backup_db = Database("Backup", "postgresql://backup:5432/app")
analytics_db = Database("Analytics", "postgresql://analytics:5432/warehouse")

container.add(Database, primary_db, qualifier="primary")
container.add(Database, backup_db, qualifier="backup")
container.add(Database, analytics_db, qualifier="analytics")

@injectable
def process_data(
    primary: Inject[Database, Options(qualifier="primary")],
    backup: Inject[Database, Options(qualifier="backup")],
    analytics: Inject[Database, Options(qualifier="analytics")]
):
    return f"Using {primary.name}, {backup.name}, and {analytics.name} databases"

result = container.call(process_data)
print(result)  # "Using Primary, Backup, and Analytics databases"
```

#### Mixed Qualified and Unqualified Dependencies

```python
from bevy import injectable, Inject, Options, Container, Registry
from bevy.bundled.type_factory_hook import type_factory

class Logger:
    def __init__(self, name: str = "default"):
        self.name = name

class Database:
    def __init__(self, name: str):
        self.name = name

registry = Registry()
type_factory.register_hook(registry)  # For unqualified dependencies
container = Container(registry)

# Add one qualified Database, let type_factory handle unqualified
container.add(Database, Database("SpecialDB"), qualifier="special")

@injectable
def mixed_dependencies(
    regular_db: Inject[Database],  # Created by type_factory
    special_db: Inject[Database, Options(qualifier="special")],  # Qualified
    logger: Inject[Logger]  # Created by type_factory
):
    return f"Regular: {regular_db.name}, Special: {special_db.name}, Logger: {logger.name}"

result = container.call(mixed_dependencies)
print(result)  # "Regular: Database, Special: SpecialDB, Logger: default"
```

#### Optional Qualified Dependencies

```python
from bevy import injectable, Inject, Options, Container, Registry

class Cache:
    def __init__(self, type_name: str):
        self.type = type_name
    
    def get(self, key: str):
        return f"{self.type} cached: {key}"

class UserService:
    def get_user(self, user_id: str):
        return f"User {user_id}"

registry = Registry()
container = Container(registry)

# Add services but not all cache types
container.add(UserService())
container.add(Cache, Cache("Redis"), qualifier="redis")
# Note: No "memcached" qualifier added

@injectable
def get_user_with_caching(
    user_service: Inject[UserService],
    redis_cache: Inject[Cache, Options(qualifier="redis")] | None,
    memcached_cache: Inject[Cache, Options(qualifier="memcached")] | None,
    user_id: str
):
    user = user_service.get_user(user_id)
    
    if redis_cache:
        cached = redis_cache.get(user_id)
        user += f" ({cached})"
    
    if memcached_cache:
        cached = memcached_cache.get(user_id)
        user += f" ({cached})"
    else:
        user += " (no memcached)"
    
    return user

result = container.call(get_user_with_caching, user_id="123")
print(result)  # "User 123 (Redis cached: 123) (no memcached)"
```

#### Qualifiers with Default Factories

```python
from bevy import injectable, Inject, Options, Container, Registry

class Logger:
    def __init__(self, name: str, level: str = "INFO"):
        self.name = name
        self.level = level
    
    def log(self, msg: str):
        return f"[{self.name}:{self.level}] {msg}"

def create_app_logger():
    return Logger("AppLogger", "DEBUG")

def create_security_logger():
    return Logger("SecurityLogger", "WARN")

registry = Registry()
container = Container(registry)

@injectable
def application_startup(
    # Default factory creates qualified logger if not found
    app_logger: Inject[Logger, Options(
        qualifier="app",
        default_factory=create_app_logger
    )],
    security_logger: Inject[Logger, Options(
        qualifier="security", 
        default_factory=create_security_logger
    )]
):
    app_msg = app_logger.log("Application starting")
    security_msg = security_logger.log("Security initialized")
    return f"{app_msg} | {security_msg}"

# First call creates both loggers via factories
result1 = container.call(application_startup)
print(result1)  # "[AppLogger:DEBUG] Application starting | [SecurityLogger:WARN] Security initialized"

# Subsequent calls reuse cached instances
result2 = container.call(application_startup)
print(result2)  # Same output, but no factory calls
```

#### Container Branching with Qualifiers

```python
from bevy import Container, Registry

class DatabaseConnection:
    def __init__(self, url: str):
        self.url = url

# Parent container with production databases
registry = Registry()
parent_container = Container(registry)

parent_container.add(DatabaseConnection, DatabaseConnection("prod-primary"), qualifier="primary")
parent_container.add(DatabaseConnection, DatabaseConnection("prod-backup"), qualifier="backup")
parent_container.add(DatabaseConnection, DatabaseConnection("prod-analytics"), qualifier="analytics")

# Child container for testing - override some but inherit others
test_container = parent_container.branch()
test_container.add(DatabaseConnection, DatabaseConnection("test-primary"), qualifier="primary")
# Inherits backup and analytics from parent

@injectable
def database_operations(
    primary: Inject[DatabaseConnection, Options(qualifier="primary")],
    backup: Inject[DatabaseConnection, Options(qualifier="backup")],
    analytics: Inject[DatabaseConnection, Options(qualifier="analytics")]
):
    return f"Primary: {primary.url}, Backup: {backup.url}, Analytics: {analytics.url}"

# Parent container uses all production databases
prod_result = parent_container.call(database_operations)
print(f"Production: {prod_result}")
# "Production: Primary: prod-primary, Backup: prod-backup, Analytics: prod-analytics"

# Test container overrides primary, inherits others
test_result = test_container.call(database_operations)
print(f"Testing: {test_result}")
# "Testing: Primary: test-primary, Backup: prod-backup, Analytics: prod-analytics"
```

#### Advanced: Environment-Based Qualifiers

```python
import os
from bevy import injectable, auto_inject, Inject, Options, get_container

class ApiClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key
    
    def call_api(self, endpoint: str):
        return f"Calling {self.base_url}/{endpoint} with key {self.api_key[:8]}..."

def create_dev_api():
    return ApiClient("https://dev-api.example.com", "dev-key-12345")

def create_prod_api():
    return ApiClient("https://api.example.com", os.getenv("PROD_API_KEY", "fallback"))

# Environment-based setup
environment = os.getenv("ENVIRONMENT", "development")
container = get_container()

if environment == "production":
    container.add(ApiClient, create_prod_api(), qualifier="primary")
else:
    container.add(ApiClient, create_dev_api(), qualifier="primary")

@auto_inject
@injectable  
def make_api_call(
    api: Inject[ApiClient, Options(qualifier="primary")],
    endpoint: str
):
    return api.call_api(endpoint)

result = make_api_call(endpoint="users")
print(result)  # Uses dev or prod API based on environment
```

#### Common Qualifier Patterns

```python
# Database patterns
primary_db: Inject[Database, Options(qualifier="primary")]
read_replica: Inject[Database, Options(qualifier="read_replica")]
analytics_db: Inject[Database, Options(qualifier="analytics")]

# Logger patterns  
app_logger: Inject[Logger, Options(qualifier="app")]
access_logger: Inject[Logger, Options(qualifier="access")]
error_logger: Inject[Logger, Options(qualifier="error")]

# Cache patterns
user_cache: Inject[Cache, Options(qualifier="users")]
session_cache: Inject[Cache, Options(qualifier="sessions")]
content_cache: Inject[Cache, Options(qualifier="content")]

# Environment patterns
dev_config: Inject[Config, Options(qualifier="development")]
prod_config: Inject[Config, Options(qualifier="production")]
test_config: Inject[Config, Options(qualifier="testing")]
```

#### Troubleshooting Qualifiers

```python
from bevy import injectable, Inject, Options, Container, Registry

# Common issues and solutions:

# 1. Missing qualified dependency
@injectable
def missing_qualifier_example(db: Inject[Database, Options(qualifier="missing")]):
    return db.name
# Error: "Cannot resolve qualified dependency Database with qualifier 'missing'"

# 2. Typo in qualifier name
container.add(Database, Database("Test"), qualifier="primery")  # Typo!
@injectable
def typo_example(db: Inject[Database, Options(qualifier="primary")]):  # Won't match
    return db.name
# Error: "Cannot resolve qualified dependency Database with qualifier 'primary'"

# 3. Mixed qualified/unqualified confusion
container.add(Database, Database("Test"))  # Unqualified
@injectable
def confusion_example(db: Inject[Database, Options(qualifier="default")]):  # Won't match
    return db.name
# Error: Unqualified instances don't match qualified requests

# Solutions:
# - Use debug=True to see resolution process
# - Check qualifier spelling carefully
# - Remember unqualified != qualified with any qualifier
# - Use optional types for missing qualifiers: Inject[T, Options(qualifier="...")] | None
```

### Hooks for Lifecycle Management

Hooks provide powerful extension points for customizing dependency creation:

```python
from bevy import Registry, Container
from bevy.hooks import hooks
from bevy.bundled.type_factory_hook import type_factory
from tramp.optionals import Optional

class Service:
    def __init__(self, name: str = "default"):
        self.name = name

@hooks.INJECTION_REQUEST
def log_injection_request(container, context):
    """Called before resolving a dependency"""
    print(f"Requesting {context.requested_type.__name__} for {context.function_name}")

@hooks.INJECTION_RESPONSE  
def log_injection_response(container, context):
    """Called after resolving a dependency"""
    print(f"Injected {context.requested_type.__name__} = {context.result}")

@hooks.POST_INJECTION_CALL
def log_execution_time(container, context):
    """Called after function execution"""
    print(f"Function {context.function_name} took {context.execution_time_ms:.2f}ms")

@hooks.GET_INSTANCE  
def custom_service_provider(container, dependency_type):
    """Custom provider that runs before normal resolution"""
    if dependency_type is Service:
        return Optional.Some(Service("custom"))
    return Optional.Nothing()

# Register hooks
registry = Registry()
type_factory.register_hook(registry)
log_injection_request.register_hook(registry)
log_injection_response.register_hook(registry)
log_execution_time.register_hook(registry)
custom_service_provider.register_hook(registry)

container = Container(registry)

@injectable(debug=True)
def use_service(service: Inject[Service]):
    return f"Using {service.name}"

result = container.call(use_service)
# Output shows all hook executions and timing
print(result)  # "Using custom"
```

### Hook Types Available

- `hooks.INJECTION_REQUEST`: Before resolving a dependency for injection
- `hooks.INJECTION_RESPONSE`: After resolving a dependency for injection
- `hooks.POST_INJECTION_CALL`: After calling function with injected dependencies
- `hooks.GET_INSTANCE`: Intercept before getting/creating an instance
- `hooks.GOT_INSTANCE`: Filter/modify an instance after it's retrieved
- `hooks.CREATE_INSTANCE`: Intercept before creating a new instance  
- `hooks.CREATED_INSTANCE`: Filter/modify an instance after it's created
- `hooks.HANDLE_UNSUPPORTED_DEPENDENCY`: Handle types with no registered factory
- `hooks.FACTORY_MISSING_TYPE`: When no factory found for a type
- `hooks.MISSING_INJECTABLE`: When dependency cannot be resolved

## Best Practices

1. **Always use @injectable or container.call()**: Functions with `Inject[T]` parameters require one of these
2. **Register type_factory hook for convenience**: Enables automatic type creation without explicit factories
3. **Use type hints consistently**: Always specify type hints with `Inject[T]` for IDE support
4. **Prefer @auto_inject for simple cases**: Combine with @injectable for automatic global injection
5. **Test with isolated containers**: Use container branching to isolate dependencies in tests
6. **Use optional dependencies appropriately**: `Inject[T | None]` for non-critical dependencies
7. **Configure debug mode during development**: Helps understand injection behavior

## Common Patterns

### Repository Pattern with Interface
```python
from abc import ABC, abstractmethod
from bevy import injectable, auto_inject, Inject, get_container
from bevy.bundled.type_factory_hook import type_factory

class UserRepository(ABC):
    @abstractmethod
    def get_user(self, user_id: int): pass

class Database:
    def query(self, sql: str):
        return f"Query result: {sql}"

class DatabaseUserRepository(UserRepository):
    def __init__(self, db: Database):
        self.db = db
    
    def get_user(self, user_id: int):
        return self.db.query(f"SELECT * FROM users WHERE id = {user_id}")

# Set up global container with type mapping
container = get_container()
type_factory.register_hook(container.registry)

# Register concrete implementation for abstract interface
container.add(UserRepository, DatabaseUserRepository(Database()))

@auto_inject
@injectable
def get_user_service(repo: Inject[UserRepository], user_id: int):
    return repo.get_user(user_id)

result = get_user_service(user_id=123)
print(result)  # "Query result: SELECT * FROM users WHERE id = 123"
```

### Configuration Injection
```python
import os
from bevy import injectable, auto_inject, Inject, Options, get_container

class AppConfig:
    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL", "sqlite:///app.db")
        self.api_key = os.getenv("API_KEY", "default-key")

# Set up global container
container = get_container()

@auto_inject
@injectable
def initialize_app(
    config: Inject[AppConfig, Options(default_factory=AppConfig)]
):
    print(f"Connecting to {config.database_url}")
    return f"App initialized with {config.database_url}"

result = initialize_app()
print(result)  # "App initialized with sqlite:///app.db"
```

### Testing with Mock Dependencies
```python
from bevy import injectable, Inject, Container, Registry
from unittest.mock import Mock

class EmailService:
    def send_email(self, to: str, subject: str):
        return f"Sent '{subject}' to {to}"

class NotificationService:
    def __init__(self, email: EmailService):
        self.email = email
    
    def notify_user(self, user: str, message: str):
        return self.email.send_email(user, f"Notification: {message}")

@injectable
def send_notification(
    service: Inject[NotificationService],
    user: str,
    message: str
):
    return service.notify_user(user, message)

# Production container
prod_registry = Registry()
prod_container = Container(prod_registry)
prod_container.add(EmailService())
prod_container.add(NotificationService(EmailService()))

# Test container with mocks
test_registry = Registry()
test_container = Container(test_registry)

mock_email = Mock()
mock_email.send_email.return_value = "Mock email sent"
test_container.add(EmailService, mock_email)
test_container.add(NotificationService(mock_email))

# Test with mock
result = test_container.call(send_notification, user="test@example.com", message="Hello")
mock_email.send_email.assert_called_once()
print(result)  # "Mock email sent"
```

## Migration from Bevy 3.0 Beta

### Old System (3.0 beta)
```python
# OLD - Bevy 3.0 beta
from bevy import inject, dependency

@inject
def old_function(service: UserService = dependency()):
    return service.process()
```

### Current System (3.1 beta)
```python
# Bevy 3.1 beta
from bevy import injectable, auto_inject, Inject

@auto_inject
@injectable
def process_user(service: Inject[UserService]):
    return service.process()
```

### Key Changes
1. Replace `dependency()` defaults with `Inject[T]` type annotations
2. Replace `@inject` with `@injectable` (or `@auto_inject` + `@injectable`)
3. Remove default parameter values - types are inferred from annotations
4. Add type_factory hook for automatic type creation
5. Use `Options` for advanced dependency configuration

## Troubleshooting

- **Missing dependencies**: Ensure `type_factory` hook is registered or add explicit factories
- **Type errors**: Verify `Inject[T]` annotations are used correctly
- **Global context issues**: Check `BEVY_ENABLE_GLOBAL_CONTEXT` environment variable
- **Decorator order**: `@auto_inject` must come before `@injectable`
- **Circular dependencies**: Use factory functions or lazy initialization

---

**That's it!** You now have everything needed to start using Bevy 3.x for dependency injection in your Python applications. The framework handles the complexity while keeping your code clean, type-safe, and testable.