# Bevy Documentation

**Bevy** is a modern, type-safe dependency injection framework for Python 3.12+ that makes managing dependencies simple and elegant.

## Quick Links

- **[Quick Start Guide](../BEVY_QUICKSTART.md)** - Get up and running in minutes
- **[Usage Guide](usage-guide.md)** - Patterns and best practices
- **[API Reference](api.md)** - Complete API documentation  
- **[Migration Guide](migration.md)** - Upgrade from Bevy 3.0 beta

## What is Bevy?

Bevy provides elegant dependency injection for Python applications using modern type hints and decorators. It enables you to write loosely coupled, testable code while maintaining full IDE support and type safety.

### Key Features

- **🎯 Type Safe**: Full IDE autocomplete and type checking with `Inject[T]`
- **🚀 Python 3.12+**: Leverages modern type system features
- **🔧 Flexible**: Multiple injection strategies for different use cases
- **🔍 Debuggable**: Rich debug mode and execution tracking
- **🪝 Extensible**: Powerful hook system for customization
- **⚡ Fast**: Optimized dependency resolution with caching
- **🧪 Testable**: Container branching for test isolation

## Basic Example

```python
from bevy import injectable, auto_inject, Inject, get_container
from bevy.bundled.type_factory_hook import type_factory

# Define your services
class UserService:
    def get_user(self, user_id: str):
        return f"User {user_id}"

class EmailService:
    def send_email(self, to: str, subject: str):
        return f"Sent '{subject}' to {to}"

# Set up global container
container = get_container()
type_factory.register_hook(container.registry)

# Use dependency injection
@auto_inject
@injectable
def notify_user(
    user_service: Inject[UserService],
    email_service: Inject[EmailService],
    user_id: str,
    message: str
):
    user = user_service.get_user(user_id)
    return email_service.send_email(user, f"Notification: {message}")

# Call directly - dependencies injected automatically
result = notify_user(user_id="123", message="Welcome!")
print(result)  # "Sent 'Notification: Welcome!' to User 123"
```

## Core Concepts

### Decorators

- **`@injectable`** - Enables dependency injection for functions
- **`@auto_inject`** - Automatically uses global container for injection
  - When you call an auto-injected function through `Container.call`, its dependencies come from the container that invoked it.
  - If another decorator wraps the auto-injected callable afterwards, the wrapper receives dependencies from the calling container while the inner function still uses the global container. This intentional double-injection avoids breaking existing decorators.

### Type System

- **`Inject[T]`** - Declares a parameter as injectable
- **`Inject[T | None]`** - Optional dependency (can be None)
- **`Options(...)`** - Configuration for dependency behavior

### Container Management

- **`Container`** - Manages dependency instances and injection
- **`Registry`** - Stores factories and hooks for dependency creation
- **`container.branch()`** - Create isolated containers for testing

## Advanced Features

### Qualified Dependencies

Use multiple instances of the same type:

```python
from bevy import Options

@injectable
def database_operations(
    primary_db: Inject[Database, Options(qualifier="primary")],
    backup_db: Inject[Database, Options(qualifier="backup")]
):
    # Use different database instances
    pass

# Set up qualified instances
container.add(Database, primary_db, qualifier="primary")
container.add(Database, backup_db, qualifier="backup")
```

### Default Factories

Provide fallback instances when dependencies aren't found:

```python
@injectable
def app_startup(
    config: Inject[AppConfig, Options(default_factory=lambda: AppConfig("default"))],
    logger: Inject[Logger, Options(default_factory=create_logger)]
):
    # Config and logger created by factories if not in container
    pass
```

### Injection Strategies

Control which parameters get injected:

```python
from bevy import InjectionStrategy

# Only inject Inject[T] parameters (default)
@injectable
def explicit_injection(service: Inject[UserService], manual: str):
    pass

# Inject any typed parameter not provided
@injectable(strategy=InjectionStrategy.ANY_NOT_PASSED)
def auto_injection(service: UserService, manual: str):
    pass
```

### Hook System

Customize dependency creation and injection:

```python
from bevy.hooks import hooks

@hooks.INJECTION_REQUEST
def log_injection_request(container, context):
    print(f"Injecting {context.requested_type.__name__}")

@hooks.POST_INJECTION_CALL
def log_execution_time(container, context):
    print(f"Executed in {context.execution_time_ms:.2f}ms")

# Register hooks
registry = get_registry()
log_injection_request.register_hook(registry)
log_execution_time.register_hook(registry)
```

## Getting Started

1. **Install Bevy**:
   ```bash
   pip install bevy>=3.1.0
   ```

2. **Follow the Quick Start**: See [BEVY_QUICKSTART.md](../BEVY_QUICKSTART.md) for detailed examples

3. **Explore the API**: Check out [API Reference](api.md) for complete documentation

4. **Migrate from 3.0**: Use [Migration Guide](migration.md) if upgrading

## Why Choose Bevy?

### Type Safety
Full IDE support with autocomplete, refactoring, and type checking:

```python
@injectable
def process_user(service: Inject[UserService]):  # IDE knows this is UserService
    service.get_user("123")  # Autocomplete available
```

### Testing
Easy test isolation with container branching:

```python
# Production container
prod_container = get_container()
prod_container.add(DatabaseService("production"))

# Test container with mocks
test_container = prod_container.branch()
test_container.add(DatabaseService("test"))  # Override for testing
```

### Performance
Optimized dependency resolution with intelligent caching:

```python
# Expensive factory called only once
@injectable
def service_a(db: Inject[Database, Options(default_factory=create_expensive_db)]):
    pass

@injectable  
def service_b(db: Inject[Database, Options(default_factory=create_expensive_db)]):
    pass  # Reuses cached instance from service_a
```

### Debugging
Rich debug information for troubleshooting:

```python
@injectable(debug=True)
def debug_function(service: Inject[UserService]):
    pass

# Output:
# [BEVY DEBUG] Resolving <class 'UserService'> with options None
# [BEVY DEBUG] Injected service: <class 'UserService'> = <UserService object>
```

## Best Practices

1. **Use type hints consistently** - Always provide `Inject[T]` annotations
2. **Register type_factory hook** - Enables automatic type creation  
3. **Prefer @auto_inject for simple cases** - Reduces boilerplate
4. **Use container branching for tests** - Isolate test dependencies
5. **Handle optional dependencies** - Use `T | None` for non-critical services
6. **Enable debug mode during development** - Understand injection behavior

## Community and Support

- **Source Code**: [GitHub Repository](https://github.com/ZechCodes/Bevy)
- **Issues**: [Report bugs and request features](https://github.com/ZechCodes/Bevy/issues)
- **Discussions**: [Community discussions](https://github.com/ZechCodes/Bevy/discussions)

## License

Bevy is licensed under the MIT License. See [LICENSE](../LICENSE) for details.
