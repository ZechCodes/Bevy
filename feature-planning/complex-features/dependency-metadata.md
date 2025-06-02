# Dependency Metadata System Overhaul

## Overview
The current dependency metadata system using `dependency()` creates significant usability and type safety issues. This document outlines a complete overhaul to create a modern, type-safe, and intuitive dependency injection API.

## Current System Issues

### 1. Type Safety Violations
```python
# Current problematic approach
@inject
def my_function(user_service=dependency()):
    # IDE thinks user_service is Any/dependency object, not UserService
    # No autocomplete or type checking
    pass
```

**Problems:**
- Parameters appear as `dependency` objects instead of actual service types
- No IDE autocomplete or type checking
- `dependency()` returns `Any`, hiding actual types
- Static analysis tools can't understand injection intent

### 2. Magic Behavior and Confusion
```python
# Current confusing patterns
@inject
def func1(service: UserService): pass  # Sometimes works?

@inject  
def func2(service=dependency()): pass  # Sometimes required?

container.call(func1)  # Why both @inject and container.call?
```

**Problems:**
- Unclear when `dependency()` is required vs optional
- Magic behavior with default parameters
- Confusing interaction between `@inject` and `container.call()`
- No clear guidelines on when to use which approach

### 3. Limited Metadata Capabilities
**Problems:**
- No support for qualifiers to distinguish multiple implementations
- No optional dependency support for graceful degradation
- No configuration binding capabilities
- No advanced injection strategies

### 4. API Inconsistency
**Problems:**
- Multiple ways to achieve similar results
- Overlapping responsibilities between decorators and functions
- Non-obvious parameter binding behavior
- Complex interaction between decorators and metadata

## Proposed Solution

### 1. Modern Type-Safe API Using Python 3.12+ Features

#### Core Type System
```python
# New type alias using Python 3.12+ type keyword
type Inject[T, Opts: object] = Annotated[T, Opts]

# Usage preserves actual types
def my_function(user_service: Inject[UserService]): 
    # IDE knows user_service is UserService
    # Full autocomplete and type checking
    pass
```

#### Metadata Options
```python
class Options:
    def __init__(
        self,
        qualifier: Optional[str] = None,
        from_config: Optional[str] = None,
        default_factory: Optional[Callable] = None
    ):
        self.qualifier = qualifier
        self.from_config = from_config
        self.default_factory = default_factory
```

**Important:** Optional dependencies are handled through type annotations (`Inject[SomeType | None]`) rather than an `optional` parameter. This maintains type correctness - if a parameter is typed as `Inject[SomeType]`, it should never receive `None`.

#### Type-Safe Optional Dependencies
```python
# Required dependency - never None
@injectable
def required_function(service: Inject[UserService]):
    # service is guaranteed to be UserService, never None
    service.process_data()  # Safe to call methods

# Optional dependency - may be None  
@injectable
def optional_function(service: Inject[UserService | None]):
    # service may be None, type checker enforces null checks
    if service:
        service.process_data()  # Only called when not None
    else:
        # Handle graceful degradation
        print("Service not available")

# Mixed required and optional
@injectable  
def mixed_function(
    required_db: Inject[Database],           # Never None
    optional_cache: Inject[Cache | None],    # May be None
    optional_metrics: Inject[MetricsService | None]  # May be None
):
    # Use required database
    data = required_db.get_data()
    
    # Use cache if available
    if optional_cache:
        optional_cache.store(data)
    
    # Report metrics if available
    if optional_metrics:
        optional_metrics.increment("data_processed")
```

### 2. Separated Decorator Responsibilities

#### `@injectable` - Pure Metadata Configuration
```python
@injectable(
    strategy=InjectionStrategy.DEFAULT,
    strict=True,
    type_matching=TypeMatchingStrategy.DEFAULT,
    debug=False,
    cache_analysis=True
)
def my_function(service: Inject[UserService]):
    # Function is configured for injection but no runtime behavior yet
    pass
```

#### `@auto_inject` - Runtime Behavior
```python
@injectable
@auto_inject
def my_function(service: Inject[UserService]):
    # Function now automatically injects from global container when called
    pass
```

### 3. Flexible Injection Strategies

```python
class InjectionStrategy(Enum):
    DEFAULT = "default"                  # Maps to REQUESTED_ONLY
    REQUESTED_ONLY = "requested_only"    # Only inject Inject[T] parameters
    ANY_NOT_PASSED = "any_not_passed"    # Inject any typed param not passed
    ONLY = "only"                        # Inject only specified parameters

class TypeMatchingStrategy(Enum):
    DEFAULT = "default"                  # Maps to SUBCLASS
    SUBCLASS = "subclass"                # Allow subclasses (current behavior)
    STRUCTURAL = "structural"            # Allow protocols/duck typing
    EXACT_TYPE = "exact_type"            # Exact type match only
```

## Implementation Details

### 1. Type Introspection System
```python
from typing import get_origin, get_args

def extract_injection_info(annotation):
    """Extract injection metadata from type annotation."""
    if get_origin(annotation) is Inject:
        args = get_args(annotation)
        actual_type = args[0]
        options = args[1] if len(args) > 1 else None
        return actual_type, options
    return annotation, None
```

### 2. Decorator Implementation
```python
def injectable(
    strategy: InjectionStrategy = InjectionStrategy.DEFAULT,
    params: Optional[list[str]] = None,
    strict: bool = True,
    type_matching: TypeMatchingStrategy = TypeMatchingStrategy.DEFAULT,
    debug: bool = False,
    cache_analysis: bool = True
):
    # Convert DEFAULT enums to actual strategies
    actual_strategy = (InjectionStrategy.REQUESTED_ONLY 
                      if strategy == InjectionStrategy.DEFAULT 
                      else strategy)
    actual_type_matching = (TypeMatchingStrategy.SUBCLASS 
                           if type_matching == TypeMatchingStrategy.DEFAULT 
                           else type_matching)
    
    def decorator(func):
        # Analyze function signature and store metadata
        injection_params = analyze_function_signature(func, actual_strategy, params)
        
        # Store all configuration on function
        func._bevy_injection_params = injection_params
        func._bevy_injection_strategy = actual_strategy
        func._bevy_type_matching = actual_type_matching
        func._bevy_strict_mode = strict
        func._bevy_debug_mode = debug
        func._bevy_cache_analysis = cache_analysis
        return func
    return decorator

def auto_inject(func):
    """Enable automatic injection using global container."""
    if not hasattr(func, '_bevy_injection_params'):
        raise ValueError(f"Function {func.__name__} must be decorated with @injectable first")
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Get global container and perform injection
        container = get_global_container()
        return container.call(func, *args, **kwargs)
    
    return wrapper
```

### 3. Container Integration
```python
class Container:
    def call(self, func, *args, **kwargs):
        """Call function with dependency injection."""
        if hasattr(func, '_bevy_injection_params'):
            # Use stored metadata from @injectable
            injection_params = func._bevy_injection_params
            type_matching = func._bevy_type_matching
            strict_mode = func._bevy_strict_mode
            debug_mode = func._bevy_debug_mode
        else:
            # Analyze function signature dynamically
            injection_params = analyze_function_signature(func, InjectionStrategy.ANY_NOT_PASSED)
            type_matching = TypeMatchingStrategy.SUBCLASS
            strict_mode = True
            debug_mode = False
        
        # Perform injection using metadata
        return self._inject_and_call(func, injection_params, *args, **kwargs)
```

## Usage Examples

### Simple Explicit Injection (Most Common)
```python
@injectable
@auto_inject
def handle_request(
    user_service: Inject[UserService],
    request_id: str
):
    return user_service.process_request(request_id)

# Usage: handle_request("12345")
# user_service automatically injected from global container
```

### Auto-Injection Convenience
```python
@injectable(strategy=InjectionStrategy.ANY_NOT_PASSED)
@auto_inject
def process_data(
    user_service: UserService,    # Auto-injected if not passed
    db: Database,                 # Auto-injected if not passed
    data: str                     # Must be passed manually
):
    return user_service.save_to_db(db, data)

# Usage: process_data("my data")
# user_service and db automatically injected
```

### Complex Metadata
```python
@injectable
@auto_inject
def complex_handler(
    primary_db: Inject[Database, Options(qualifier="primary")],
    cache: Inject[Cache | None],  # Optional via type annotation
    config: Inject[dict, Options(from_config="app.settings")]
):
    if cache:
        # Use cache if available
        pass
    # Use primary database and config
    pass
```

### Explicit Container Usage (No auto_inject)
```python
@injectable(strategy=InjectionStrategy.ANY_NOT_PASSED)
def business_logic(user_service: UserService, data: str):
    return user_service.process(data)

# Explicit injection via container
result = container.call(business_logic, data="example")
```

### Advanced Configuration
```python
@injectable(
    strategy=InjectionStrategy.REQUESTED_ONLY,
    strict=False,  # Missing dependencies become None
    type_matching=TypeMatchingStrategy.STRUCTURAL,  # Duck typing
    debug=True,  # Log injection activities
    cache_analysis=True  # Cache for performance
)
@auto_inject
def advanced_function(
    service: Inject[UserService | None],  # Optional via type annotation
    protocol_impl: Inject[StorageProtocol]
):
    # service may be None if not available (strict=False + union type)
    # protocol_impl accepts any object with required methods (structural typing)
    if service:
        # Use service if available
        pass
```

## Breaking Changes from Current System

### 1. Removed Components
- **`dependency()` function** - Completely removed
- **`dependencies.py` module** - Deleted
- **Magic `Any` return types** - No longer supported
- **Current `@inject` decorator** - Replaced with `@injectable` + `@auto_inject`

### 2. New Required Components
- **`type Inject[T, Opts]`** - New type alias (requires Python 3.12+)
- **`Options` class** - For injection metadata
- **`InjectionStrategy` enum** - For injection behavior
- **`TypeMatchingStrategy` enum** - For type resolution behavior
- **`@injectable` decorator** - For configuration
- **`@auto_inject` decorator** - For automatic injection

### 3. Migration Examples
```python
# Old approach
@inject
def old_function(user_service=dependency()):
    pass

# New approach
@injectable
@auto_inject
def new_function(user_service: Inject[UserService]):
    pass
```

## Implementation Checklist

### Phase 1: Core Type System (Week 1)
- [ ] **Update minimum Python version to 3.12+** in `pyproject.toml`
- [ ] **Create new module** `bevy/injection_types.py`
  - [ ] Implement `type Inject[T, Opts]` alias
  - [ ] Create `Options` class with all metadata fields
  - [ ] Create `InjectionStrategy` enum with all strategies
  - [ ] Create `TypeMatchingStrategy` enum with type matching options
- [ ] **Update package version** to `3.1.0-beta.1` in `pyproject.toml`
- [ ] **Add type introspection utilities**
  - [ ] `extract_injection_info()` function
  - [ ] `analyze_function_signature()` function

### Phase 2: New Decorator System (Week 1-2)
- [ ] **Rewrite `injections.py`**
  - [ ] Remove old `inject()` decorator completely
  - [ ] Implement new `injectable()` decorator with all configuration options
  - [ ] Implement new `auto_inject()` decorator
  - [ ] Add function metadata storage system
  - [ ] Add DEFAULT enum conversion logic
- [ ] **Update module exports** in `bevy/__init__.py`
  - [ ] Remove `dependency` export
  - [ ] Add `Inject`, `Options`, `InjectionStrategy`, `TypeMatchingStrategy` exports
  - [ ] Add `injectable`, `auto_inject` exports
  - [ ] Update `__all__` list

### Phase 3: Container Integration (Week 2)
- [ ] **Update `containers.py`**
  - [ ] Modify `call()` method to use new metadata system
  - [ ] Add support for all injection strategies
  - [ ] Add support for all type matching strategies
  - [ ] Add strict mode handling (None vs exceptions)
  - [ ] Add debug mode logging
  - [ ] Add parameter analysis caching
- [ ] **Update `factories.py`**
  - [ ] Update factory parameter inspection for new type system
  - [ ] Add `Inject[T]` detection in factory signatures
  - [ ] Remove old `dependency()` parameter handling

### Phase 4: Hook System Updates (Week 2)
- [ ] **Update `hooks.py`**
  - [ ] Update hook context to include new injection metadata
  - [ ] Add support for `Options` in hook context
  - [ ] Remove legacy dependency metadata from hooks
  - [ ] Update all built-in hooks for new system

### Phase 5: Complete Test Rewrite (Week 3)
- [ ] **Rewrite `tests/test_bevy.py`**
  - [ ] Remove all `dependency()` test cases
  - [ ] Add comprehensive tests for `@injectable` decorator
  - [ ] Add comprehensive tests for `@auto_inject` decorator  
  - [ ] Add tests for all injection strategies
  - [ ] Add tests for all type matching strategies
  - [ ] Add tests for `Inject[T, Options]` syntax variations
  - [ ] Add tests for qualifier functionality
  - [ ] Add tests for optional dependency functionality via `Inject[Type | None]`
  - [ ] Add tests for strict mode vs graceful degradation
  - [ ] Add tests for debug mode logging
  - [ ] Add tests for caching behavior
- [ ] **Update `tests/test_hooks.py`**
  - [ ] Update all hook tests for new injection metadata
  - [ ] Remove old dependency metadata test cases
  - [ ] Add tests for new hook context information

### Phase 6: Documentation Overhaul (Week 3-4)
- [ ] **Update `README.md`**
  - [ ] Replace all `dependency()` examples with `Inject[T]` syntax
  - [ ] Add injection strategy examples
  - [ ] Add qualifier and optional dependency examples
  - [ ] Add `@injectable` + `@auto_inject` pattern examples
  - [ ] Add migration guide section with before/after examples
- [ ] **Update `BEVY_QUICKSTART.md`**
  - [ ] Replace quick start examples with new syntax
  - [ ] Add strategy selection guidance
  - [ ] Show progression from simple to complex usage
- [ ] **Create comprehensive guides** in `docs/` directory:
  - [ ] **`injection-strategies.md`** - Complete guide to all injection strategies
  - [ ] **`type-safety.md`** - Guide to type-safe dependency injection
  - [ ] **`qualifiers-and-options.md`** - Advanced metadata usage
  - [ ] **`decorator-patterns.md`** - When to use @injectable vs @auto_inject
  - [ ] **`migration-guide.md`** - Complete migration from old to new system
  - [ ] **`troubleshooting.md`** - Common issues and debugging
- [ ] **Update API documentation**
  - [ ] Generate new API docs for all new classes and functions
  - [ ] Remove old `dependency()` documentation
  - [ ] Add comprehensive examples for each feature

### Phase 7: Error Handling and Messages (Week 4)
- [ ] **Enhance error messages** throughout codebase
  - [ ] Update all error messages to reference `Inject[T]` syntax
  - [ ] Add strategy-specific error guidance
  - [ ] Add helpful suggestions for common mistakes
  - [ ] Add qualification-specific error messages
- [ ] **Add validation and warnings**
  - [ ] Validate `@auto_inject` requires `@injectable`
  - [ ] Warn about common migration issues
  - [ ] Add helpful error messages for type system issues

### Phase 8: Performance and Polish (Week 4-5)
- [ ] **Implement caching systems**
  - [ ] Add signature analysis caching
  - [ ] Add type introspection result caching
  - [ ] Add performance monitoring hooks
- [ ] **Add debug and development tools**
  - [ ] Implement debug mode logging
  - [ ] Add injection tracing capabilities
  - [ ] Create development utilities for troubleshooting
- [ ] **Final integration testing**
  - [ ] End-to-end testing of all features
  - [ ] Performance regression testing
  - [ ] Memory usage validation

### Phase 9: Build System and CI (Week 5)
- [ ] **Update build configuration**
  - [ ] Verify Python 3.12+ requirement in all configs
  - [ ] Update CI/CD pipelines for new Python version
  - [ ] Add mypy configuration for new type system
  - [ ] Update linting rules for new patterns
- [ ] **Update package metadata**
  - [ ] Confirm version bump to `3.1.0-beta.1`
  - [ ] Update package description and keywords
  - [ ] Update classifiers for new Python version requirement

### Phase 10: Release Preparation (Week 5)
- [ ] **Create comprehensive changelog**
  - [ ] Document all breaking changes
  - [ ] List all new features
  - [ ] Provide migration examples
- [ ] **Final documentation review**
  - [ ] Review all documentation for accuracy
  - [ ] Ensure all examples work with new system
  - [ ] Verify migration guide completeness
- [ ] **Release testing**
  - [ ] Test package installation and usage
  - [ ] Verify all examples in documentation work
  - [ ] Confirm breaking changes are properly documented

## Estimated Timeline
**Total Duration: 5 weeks**

- **Week 1**: Core type system and decorator implementation
- **Week 2**: Container integration and hook updates
- **Week 3**: Complete test suite rewrite
- **Week 4**: Documentation and error handling
- **Week 5**: Performance optimization and release preparation

## Success Criteria
- [ ] All existing functionality works with new API
- [ ] Full type safety with IDE support and mypy compatibility
- [ ] Comprehensive test coverage (>95%)
- [ ] Complete documentation with migration guide
- [ ] No performance regression from current system
- [ ] Clean, intuitive API that follows Python best practices

This overhaul will transform Bevy into a modern, type-safe, and highly usable dependency injection framework that leverages the latest Python features while maintaining the flexibility and power users expect.