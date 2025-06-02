# Async Support

## Overview
Full async/await support for dependency injection in async applications and frameworks.

## Current Gap
- No async factory functions support
- No async dependency resolution
- No async hooks
- Missing async context management
- `@inspect.markcoroutinefunction` decorator exists but unused

## Why This Matters
- Modern Python applications are increasingly async
- Web frameworks like FastAPI, Starlette require async support
- Database connections, HTTP clients often async
- Async context propagation needed for proper isolation

## Implementation Options

### Option 1: Parallel Async/Sync APIs
- Maintain sync API, add parallel async API
- `await container.aget()` alongside `container.get()`
- Pros: Backward compatible, clear separation
- Cons: API duplication, maintenance burden

### Option 2: Unified Smart API
- Single API that detects async context and behaves appropriately
- Auto-detection of async vs sync environments
- Pros: Clean API, no duplication
- Cons: Magic behavior, potential confusion

### Option 3: Async-First Design
- Make async the primary API, provide sync wrappers
- Modern approach aligned with async frameworks
- Pros: Future-proof, consistent async patterns
- Cons: Breaking change for existing sync users

## Suggested Implementation Checklist

### Phase 1: Async Factory Support
- [ ] Support async factory functions with `async def`
- [ ] Implement `await container.aget()` for async resolution
- [ ] Add async factory registration methods
- [ ] Handle mixed async/sync dependency chains

### Phase 2: Async Hooks
- [ ] Support async hook functions
- [ ] Implement async hook execution pipeline
- [ ] Add async context passing to hooks
- [ ] Handle hook timeouts and cancellation

### Phase 3: Async Context Management
- [ ] Async context variable support for scoping
- [ ] Async container context managers
- [ ] Async scope lifecycle management
- [ ] Task-local instance storage

### Phase 4: Async Lifecycle
- [ ] Async disposal and cleanup methods
- [ ] Async startup/shutdown hooks
- [ ] Background task dependency injection
- [ ] Async health checks and monitoring

### Phase 5: Framework Integration
- [ ] FastAPI integration and middleware
- [ ] Starlette dependency injection
- [ ] aiohttp integration
- [ ] Django async views support

## API Design Examples

### Async Factories:
```python
@inject
async def create_database() -> Database:
    db = Database()
    await db.connect()
    return db

@inject  
async def create_user_service(db: Database) -> UserService:
    service = UserService(db)
    await service.initialize()
    return service
```

### Async Resolution:
```python
# Async dependency resolution
async def handle_request():
    user_service = await container.aget(UserService)
    users = await user_service.get_all_users()
    return users

# Mixed sync/async chains
@inject
def sync_service(async_db: Database) -> SyncService:
    # async_db resolved asynchronously, then passed to sync factory
    return SyncService(async_db)
```

### Async Hooks:
```python
@container.add_async_hook("injection_request")
async def log_injection(context):
    await logger.log(f"Injecting {context.requested_type}")

@container.add_async_hook("post_injection_call")
async def setup_instance(context):
    if hasattr(context.instance, 'async_setup'):
        await context.instance.async_setup()
```

### Async Context Management:
```python
async with container.create_async_scope("request") as scope:
    # Async scoped dependencies
    user_service = await scope.aget(UserService)
    await user_service.process_request()
# Automatic async cleanup
```

### Framework Integration Examples:

#### FastAPI:
```python
from bevy.integrations.fastapi import BevyDepends

app = FastAPI()

@app.get("/users")
async def get_users(user_service: UserService = BevyDepends()):
    return await user_service.get_all()
```

#### Starlette:
```python
from bevy.integrations.starlette import inject_dependencies

@inject_dependencies
async def endpoint(request, user_service: UserService):
    users = await user_service.get_users()
    return JSONResponse({"users": users})
```

## Technical Implementation Details

### Async Detection:
- Use `asyncio.iscoroutinefunction()` to detect async factories
- Check current event loop to determine if in async context
- Support both `async def` and `@coroutine` decorated functions

### Dependency Chain Resolution:
- Build dependency graph with async/sync markers
- Resolve async dependencies concurrently where possible
- Handle mixed async/sync chains gracefully

### Context Propagation:
- Use `contextvars` for async-local storage
- Maintain dependency context across `await` boundaries
- Support task cancellation and cleanup

### Performance Optimization:
- Concurrent resolution of independent async dependencies
- Connection pooling for async resources
- Lazy initialization for expensive async resources

## Error Handling Considerations

### Async Errors:
- Proper exception propagation across async boundaries
- Timeout handling for slow async factories
- Cancellation support for long-running operations

### Mixed Context Errors:
- Clear errors when calling sync methods in async context
- Guidance for resolving sync/async conflicts
- Deadlock detection and prevention

## Testing Support

### Async Testing Utilities:
```python
@pytest.mark.asyncio
async def test_async_injection():
    async with TestContainer() as container:
        service = await container.aget(UserService)
        result = await service.get_user(1)
        assert result is not None
```

## Migration Strategy
- Keep existing sync API unchanged
- Add async variants with clear naming (`aget`, `aregister`, etc.)
- Provide migration guide and tooling
- Support gradual adoption

## Priority: High
Critical for modern async Python applications.

## Estimated Effort: High
Significant architectural changes affecting core resolution logic.