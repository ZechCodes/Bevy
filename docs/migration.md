# Migration Guide: Bevy 3.0 Beta to 3.1 Beta

This guide will help you migrate your code from Bevy 3.0 beta to the new 3.1 beta injection system.

## Overview of Changes

Bevy 3.1 beta introduces a completely new dependency injection system with the following key improvements:

- ✅ **Type-safe**: Full IDE autocomplete and type checking with `Inject[T]`
- ✅ **Python 3.12+ features**: Uses modern type system with `type` keyword
- ✅ **Rich hook system**: Enhanced extensibility with detailed context
- ✅ **Better debugging**: Comprehensive debug mode and execution tracking
- ✅ **Flexible strategies**: Multiple injection strategies for different use cases
- ✅ **Optional dependencies**: Native support for `T | None` types

## Breaking Changes

### 1. Decorator Changes

**Before (3.0 beta):**
```python
from bevy import inject, dependency

@inject
def process_data(service: UserService = dependency()):
    return service.process()
```

**After (3.1 beta):**
```python
from bevy import injectable, auto_inject, Inject

# Option 1: Use with container
@injectable
def process_data(service: Inject[UserService]):
    return service.process()

# Option 2: Use with global container
@auto_inject
@injectable
def process_data(service: Inject[UserService]):
    return service.process()
```

### 2. Type Annotations

**Before (3.0 beta):**
```python
# Default parameter approach
def func(service: UserService = dependency()): pass
```

**After (3.1 beta):**
```python
# Type annotation approach
def func(service: Inject[UserService]): pass
```

### 3. Factory Functions

**Before (3.0 beta):**
```python
def custom_factory(container):
    return UserService("custom")

@inject
def func(service: UserService = dependency(custom_factory)):
    pass
```

**After (3.1 beta):**
```python
from bevy import Options

def custom_factory():
    return UserService("custom")

@injectable
def func(service: Inject[UserService, Options(default_factory=custom_factory)]):
    pass
```

## Step-by-Step Migration

### Step 1: Update Imports

**Before:**
```python
from bevy import inject, dependency, get_registry, get_container
```

**After:**
```python
from bevy import injectable, auto_inject, Inject, Options, get_registry, get_container
```

### Step 2: Replace Decorators

Replace all `@inject` decorators:

**Simple functions (global):**
```python
# OLD
@inject
def func(service: UserService = dependency()):
    pass

# NEW
@auto_inject
@injectable
def func(service: Inject[UserService]):
    pass
```

**Functions called via container:**
```python
# OLD
def func(service: UserService = dependency()):
    pass

container.call(func)

# NEW
@injectable
def func(service: Inject[UserService]):
    pass

container.call(func)
```

### Step 3: Update Parameter Declarations

Replace `dependency()` defaults with `Inject[T]` annotations:

**Basic dependencies:**
```python
# OLD
def func(
    service: UserService = dependency(),
    db: Database = dependency()
):
    pass

# NEW
def func(
    service: Inject[UserService],
    db: Inject[Database]
):
    pass
```

**Custom factories:**
```python
# OLD
def func(
    service: UserService = dependency(my_factory)
):
    pass

# NEW
def func(
    service: Inject[UserService, Options(default_factory=my_factory)]
):
    pass
```

### Step 4: Update Container Setup

**Before (3.0 beta):**
```python
from bevy import get_registry
from bevy.factories import create_type_factory

registry = get_registry()
registry.add_factory(create_type_factory(UserService))
```

**After (3.1 beta):**
```python
from bevy import get_registry
from bevy.bundled.type_factory_hook import type_factory

# Option 1: Use type_factory hook for automatic creation
registry = get_registry()
type_factory.register_hook(registry)

# Option 2: Still use explicit factories
from bevy.factories import create_type_factory
registry.add_factory(create_type_factory(UserService))
```

### Step 5: Update Class Dependencies

**Before (3.0 beta):**
```python
class UserService:
    @inject
    def __init__(self, db: Database = dependency()):
        self.db = db
```

**After (3.1 beta):**
```python
class UserService:
    @injectable
    def __init__(self, db: Inject[Database]):
        self.db = db

# Or use constructor injection automatically
class UserService:
    def __init__(self, db: Database):  # Will be injected if using ANY_NOT_PASSED
        self.db = db
```

## Common Migration Patterns

### Pattern 1: Simple Service Classes

**Before:**
```python
@inject
def get_user_data(user_id: str, service: UserService = dependency()):
    return service.get_user(user_id)

registry = get_registry()
registry.add_factory(create_type_factory(UserService))

result = get_user_data("123")
```

**After:**
```python
@auto_inject
@injectable
def get_user_data(user_id: str, service: Inject[UserService]):
    return service.get_user(user_id)

registry = get_registry()
type_factory.register_hook(registry)  # Enables automatic creation

result = get_user_data("123")
```

### Pattern 2: Container-Based Testing

**Before:**
```python
# Test setup
registry = Registry()
registry.add_factory(create_type_factory(Database, "test"))
container = registry.create_container()

def process_data(db: Database = dependency()):
    return db.process()

result = container.call(process_data)
```

**After:**
```python
# Test setup  
registry = Registry()
type_factory.register_hook(registry)
container = Container(registry)
container.add(Database("test"))  # Override default

@injectable
def process_data(db: Inject[Database]):
    return db.process()

result = container.call(process_data)
```

### Pattern 3: Optional Dependencies

**Before:**
```python
# Not directly supported - had to use try/catch or manual checks
@inject
def func(required: UserService = dependency()):
    try:
        optional = get_container().get(CacheService)
    except:
        optional = None
```

**After:**
```python
# Native support for optional dependencies
@injectable
def func(
    required: Inject[UserService],
    optional: Inject[CacheService | None]
):
    if optional:
        # Use optional service
        pass
```

### Pattern 4: Configuration-Based Dependencies

**Before:**
```python
def config_factory(container):
    return AppConfig(env="production")

@inject
def app_startup(config: AppConfig = dependency(config_factory)):
    pass
```

**After:**
```python
@injectable
def app_startup(
    config: Inject[AppConfig, Options(default_factory=lambda: AppConfig(env="production"))]
):
    pass
```

## New Features Available

### 1. Injection Strategies

Control which parameters get injected:

```python
# Only inject Inject[T] parameters (default)
@injectable
def explicit(service: Inject[UserService], manual: str): pass

# Inject any typed parameter not provided
@injectable(strategy=InjectionStrategy.ANY_NOT_PASSED)  
def auto(service: UserService, manual: str): pass

# Only inject specific parameters
@injectable(strategy=InjectionStrategy.ONLY, params=["service"])
def selective(service: UserService, manual: str): pass
```

### 2. Debug Mode

Get detailed injection logging:

```python
@injectable(debug=True)
def debug_function(service: Inject[UserService]):
    pass

# Output:
# [BEVY DEBUG] Resolving <class 'UserService'> with options None
# [BEVY DEBUG] Injected service: <class 'UserService'> = <UserService object at 0x...>
```

### 3. Rich Hook System

New hooks with detailed context:

```python
from bevy.hooks import hooks

@hooks.INJECTION_REQUEST
def log_injection_request(container, context):
    print(f"Injecting {context.requested_type.__name__} for {context.function_name}")

@hooks.POST_INJECTION_CALL
def log_execution_time(container, context):
    print(f"Function {context.function_name} took {context.execution_time_ms:.2f}ms")
```

### 4. Error Handling Options

Choose between strict and lenient error handling:

```python
# Strict mode (default) - raises errors for missing dependencies
@injectable(strict=True)
def strict_func(service: Inject[UserService]): pass

# Non-strict mode - injects None for missing dependencies
@injectable(strict=False)  
def lenient_func(service: Inject[UserService]):
    if service is None:
        # Handle gracefully
        pass
```

## Migration Checklist

- [ ] Update imports to use new decorators and types
- [ ] Replace `@inject` with `@injectable` or `@auto_inject` + `@injectable`
- [ ] Replace `dependency()` defaults with `Inject[T]` annotations
- [ ] Update factory usage to use `Options(default_factory=...)`
- [ ] Register `type_factory` hook for automatic type creation
- [ ] Update class constructors to use new injection system
- [ ] Test container setup and dependency resolution
- [ ] Update any custom hooks to use new hook types
- [ ] Consider using new optional dependency features
- [ ] Enable debug mode during migration for troubleshooting

## Troubleshooting

### Common Issues

**1. "Missing dependencies" errors**
- Ensure `type_factory` hook is registered for automatic creation
- Or add explicit factories/instances to containers

**2. "Type errors" with IDE**
- Make sure you're using `Inject[T]` annotations correctly
- Check that type imports are available in the function's namespace

**3. "@auto_inject requires @injectable" errors**
- Ensure decorator order: `@auto_inject` comes before `@injectable`

**4. "Circular import" issues**
- Use factory functions or lazy initialization
- Consider restructuring module dependencies

### Getting Help

1. **Enable debug mode**: Add `debug=True` to `@injectable` decorators
2. **Check container state**: Use `container.instances` to see what's registered
3. **Test with minimal setup**: Start with `type_factory` hook for simplicity
4. **Use container branching**: Isolate test scenarios with `container.branch()`

## Performance Considerations

The new system generally performs better due to:

- **Cached analysis**: Function signatures are analyzed once and cached
- **Optimized type checking**: Faster type resolution with new algorithms
- **Reduced overhead**: Less dynamic inspection at runtime

However, be aware that:

- **First call overhead**: Initial function analysis has some cost
- **Memory usage**: Cached analysis uses slightly more memory
- **Debug mode cost**: Debug logging has performance impact

## Conclusion

While the migration requires updating your decorators and type annotations, the new system provides:

- **Better type safety** with full IDE support
- **More powerful hooks** for extensibility  
- **Flexible injection strategies** for different scenarios
- **Native optional dependency support**
- **Improved debugging capabilities**

The effort to migrate pays off with a more robust, type-safe, and feature-rich dependency injection system.