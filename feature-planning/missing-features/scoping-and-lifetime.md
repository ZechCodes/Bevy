# Scoping and Lifetime Management

## Overview
Scoping controls when and how long dependency instances live, and when new instances are created vs reused.

## Current Gap
- Only singleton behavior available
- No concept of different instance lifetimes
- No request/session scoping
- No transient (always new) instances

## Why This Matters
- Memory management and performance optimization
- Request isolation in web applications
- Thread safety in concurrent applications
- Resource efficiency and predictable behavior

## Standard Scoping Patterns

### Singleton (Currently Supported)
- One instance per container lifetime
- Shared across all requests

### Transient (Missing)
- New instance every time requested
- No sharing or caching

### Scoped (Missing)
- One instance per scope (request, session, etc.)
- Automatic cleanup when scope ends

### Thread-Local (Missing)
- One instance per thread
- Thread-safe isolation

## Implementation Options

### Option 1: Decorator-Based Scoping
- Use decorators to specify scope: `@singleton`, `@transient`, `@scoped`
- Pros: Clear declaration, explicit control
- Cons: Requires code changes, not configurable at runtime

### Option 2: Registration-Time Scoping
- Specify scope during container registration
- Pros: Flexible, runtime configurable
- Cons: Scope not visible in factory code

### Option 3: Scope Context Management
- Explicit scope creation and management
- Pros: Full control, nested scopes
- Cons: More complex API, manual management

## Suggested Implementation Checklist

### Phase 1: Core Scoping Infrastructure
- [ ] Create `Scope` enum (SINGLETON, TRANSIENT, SCOPED, THREAD_LOCAL)
- [ ] Add scope parameter to factory registration
- [ ] Implement transient scope (always create new instance)
- [ ] Modify container resolution to respect scopes

### Phase 2: Scoped Lifetime Management
- [ ] Implement `ScopeContext` for managing scoped instances
- [ ] Add request/session scope implementations
- [ ] Support custom scope definitions
- [ ] Add scope cleanup and disposal

### Phase 3: Thread-Local Scoping
- [ ] Implement thread-local storage for instances
- [ ] Add thread-safe scope management
- [ ] Support thread pool environments
- [ ] Handle thread cleanup automatically

### Phase 4: Advanced Scoping Features
- [ ] Nested scope support (request within session)
- [ ] Scope inheritance and delegation
- [ ] Conditional scoping based on context
- [ ] Scope performance optimization

### Phase 5: Framework Integration
- [ ] Web framework middleware for automatic scoping
- [ ] Async context support for scoped instances
- [ ] Testing utilities for scope management
- [ ] Scope debugging and inspection tools

## API Design Examples

### Decorator-Based Scoping:
```python
@transient
class LogEntry:
    def __init__(self):
        self.timestamp = datetime.now()

@scoped("request")  
class UserSession:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.data = {}

@singleton
class ConfigService:
    pass
```

### Registration-Based Scoping:
```python
container.register(LogEntry, scope=Scope.TRANSIENT)
container.register(UserSession, scope=Scope.SCOPED, scope_name="request")
container.register(ConfigService, scope=Scope.SINGLETON)
```

### Manual Scope Management:
```python
with container.create_scope("request") as request_scope:
    user_session = request_scope.get(UserSession)
    # user_session lives for duration of request scope
# Automatic cleanup when scope exits
```

### Web Framework Integration:
```python
@app.middleware("http")
async def dependency_scope_middleware(request, call_next):
    with container.create_scope("request") as scope:
        request.state.container_scope = scope
        response = await call_next(request)
    # Scope automatically cleaned up
    return response
```

## Scope Definitions

### Built-in Scopes:
- **SINGLETON**: One instance per container
- **TRANSIENT**: New instance every request
- **SCOPED**: One instance per named scope
- **THREAD_LOCAL**: One instance per thread

### Custom Scopes:
```python
class CustomScope(ScopeProvider):
    def get_instance(self, factory, container):
        # Custom scoping logic
        pass
    
    def cleanup(self):
        # Custom cleanup logic
        pass

container.register_scope("custom", CustomScope())
```

## Web Application Example

### Request Scoping:
```python
# Middleware creates request scope
@app.middleware("http")
async def setup_request_scope(request, call_next):
    with container.create_scope("request") as scope:
        # Request-scoped dependencies
        scope.register(CurrentUser, factory=lambda: get_user_from_request(request))
        scope.register(RequestId, factory=lambda: str(uuid.uuid4()))
        
        request.state.scope = scope
        response = await call_next(request)
    return response

# Controllers get request-scoped dependencies
@inject
def get_profile(current_user: CurrentUser, request_id: RequestId):
    # current_user and request_id are request-scoped
    return {"user": current_user.name, "request_id": request_id}
```

## Performance Considerations

### Scope Resolution Strategy:
- Cache scope lookups for performance
- Optimize common scoping patterns
- Minimize scope creation overhead

### Memory Management:
- Automatic cleanup of expired scopes
- Weak references for transient instances
- Memory profiling for scope leaks

### Concurrency:
- Thread-safe scope management
- Async context support
- Lock-free optimizations where possible

## Migration Strategy
- Default to current singleton behavior
- Add opt-in scoping for new registrations
- Provide migration tools for existing code

## Priority: High
Essential for web applications and production usage.

## Estimated Effort: High
Major architectural feature requiring extensive testing.