# Global Context Management Complexity

## Overview
The use of context variables with environment variable control creates confusing implicit global state.

## Current Complexity Issues
- Implicit global state can be confusing and hard to debug
- Environment variable control (`BEVY_ENABLE_GLOBAL_CONTEXT`) is non-obvious
- Mixing explicit and implicit container usage
- Global state makes testing difficult
- Thread safety concerns with global context

## Why This Is Hard to Understand
- Magic behavior - containers appear from nowhere
- Environment-dependent behavior
- Implicit vs explicit API confusion
- Global state debugging challenges
- Thread safety not obvious

## Current Implementation Analysis
From `context_vars.py`:
- Uses `contextvars` for thread-local container storage
- Environment variable `BEVY_ENABLE_GLOBAL_CONTEXT` controls behavior
- Implicit container access when no explicit container provided

## Simplification Options

### Option 1: Make Global Context Explicit
- Require explicit opt-in to global context
- Clear API for global context management
- Better error messages when global context unavailable
- Pros: More predictable, easier to debug
- Cons: More verbose for simple use cases

### Option 2: Remove Global Context
- Always require explicit container passing
- Simplify to pure dependency injection
- Pros: No magic, completely predictable
- Cons: More boilerplate, breaking change

### Option 3: Improved Global Context
- Better documentation and debugging tools
- Clear scoping rules for global context
- Enhanced thread safety guarantees
- Pros: Maintains convenience, clearer behavior
- Cons: Still has complexity of global state

## Suggested Improvement Checklist

### Phase 1: Explicit Global Context Management
- [ ] Add `Container.set_global()` and `Container.get_global()` methods
- [ ] Deprecate environment variable control in favor of explicit API
- [ ] Add clear error messages when global context missing
- [ ] Document global context lifecycle clearly

### Phase 2: Scope-Aware Global Context
- [ ] Support multiple global contexts for different scopes
- [ ] Add request-scoped global context for web applications
- [ ] Implement context inheritance and isolation
- [ ] Add debugging tools for global context state

### Phase 3: Enhanced Thread Safety
- [ ] Guarantee thread-local global context behavior
- [ ] Add async context support for global context
- [ ] Implement context cleanup for completed tasks
- [ ] Add warnings for global context leaks

### Phase 4: Testing and Debugging
- [ ] Add test utilities for global context management
- [ ] Implement global context inspection tools
- [ ] Add performance monitoring for global context overhead
- [ ] Create migration tools from global to explicit context

## Clarified API Examples

### Current Confusing Usage:
```python
# Magic - where does the container come from?
@inject
def my_function(user_service: UserService):
    pass

# Environment variable controls behavior - non-obvious
os.environ["BEVY_ENABLE_GLOBAL_CONTEXT"] = "true"
```

### Explicit Global Context:
```python
# Explicit global context setup
container = Container()
container.register(UserService)
Container.set_global(container)

# Clear when using global context
@inject  # Now explicitly uses global context
def my_function(user_service: UserService):
    pass

# Or explicit container usage  
@inject(container=container)
def my_function(user_service: UserService):
    pass
```

### Scoped Global Context:
```python
# Request-scoped global context
@app.middleware("http")
async def setup_request_context(request, call_next):
    request_container = app_container.create_request_scope()
    
    with Container.global_scope(request_container):
        # All @inject calls in this scope use request_container
        response = await call_next(request)
    
    return response
```

### Clear Context Management:
```python
# Explicit context lifecycle
def setup_application():
    container = Container()
    # ... setup container ...
    Container.set_global(container)

def teardown_application():
    Container.clear_global()

# Context inspection
if Container.has_global():
    current = Container.get_global()
    print(f"Global container: {current}")
else:
    print("No global container set")
```

## Thread Safety and Async Support

### Thread-Local Behavior:
```python
# Each thread gets its own global context
import threading

def worker_thread():
    # Set thread-specific global container
    thread_container = Container()
    Container.set_thread_local_global(thread_container)
    
    # This thread's @inject calls use thread_container
    service = get_service()

# Main thread global context unaffected
threading.Thread(target=worker_thread).start()
```

### Async Context Support:
```python
# Async task-local global context
async def handle_request():
    request_container = create_request_container()
    
    async with Container.async_global_scope(request_container):
        # All async operations in this context use request_container
        result = await process_request()
    
    return result
```

## Testing Support

### Test Context Isolation:
```python
class TestMyService(unittest.TestCase):
    def setUp(self):
        # Create isolated test container
        self.test_container = Container()
        self.test_container.register(MockUserService)
        
        # Set as test-local global context
        Container.set_test_global(self.test_container)
    
    def tearDown(self):
        # Automatic cleanup
        Container.clear_test_global()
    
    def test_service_injection(self):
        # Uses test container automatically
        result = my_function_with_injection()
        self.assertIsInstance(result.user_service, MockUserService)
```

### Test Utilities:
```python
# Test decorator for automatic context management
@with_test_container
def test_my_function():
    # Test container automatically set up and torn down
    pass

# Test context manager
def test_with_mocks():
    with test_container() as container:
        container.register(MockService)
        # Test runs with mock container as global
        pass
```

## Migration Strategy

### Phase 1: Deprecate Environment Variable
- Add deprecation warnings for `BEVY_ENABLE_GLOBAL_CONTEXT`
- Provide explicit API alternatives
- Update documentation to show new patterns

### Phase 2: Encourage Explicit Usage
- Show explicit container usage in examples
- Provide migration tools for existing code
- Add lint rules for implicit global usage

### Phase 3: Remove Environment Control
- Remove environment variable dependency
- Make global context purely explicit
- Breaking change with clear migration path

## Performance Considerations

### Context Lookup Overhead:
- Cache global context lookups
- Optimize context variable access
- Minimal overhead for explicit container usage

### Memory Management:
- Automatic cleanup of expired contexts
- Weak references for context storage
- Leak detection for abandoned contexts

## Debugging Tools

### Context Inspection:
```python
# Debug global context state
debug_info = Container.get_global_debug_info()
print(f"Global containers: {debug_info.active_contexts}")
print(f"Context stack: {debug_info.context_stack}")
print(f"Thread contexts: {debug_info.thread_contexts}")
```

### Context Tracing:
```python
# Enable global context tracing
Container.enable_context_tracing()

# All global context operations logged
Container.set_global(my_container)  # [TRACE] Global context set
service = get_service()             # [TRACE] Using global context
Container.clear_global()            # [TRACE] Global context cleared
```

## Priority: Medium
Important for API clarity but not critical for core functionality.

## Estimated Effort: Medium
Requires API changes and documentation improvements but well-scoped.