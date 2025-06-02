# Lifecycle Management

## Overview
Lifecycle management is a critical missing feature that handles the creation, usage, and disposal of dependencies throughout their lifetime.

## Current Gap
- No support for instance disposal or cleanup
- No container shutdown hooks
- No resource cleanup on container disposal
- Missing context manager support for automatic cleanup

## Why This Matters
- Memory leaks from unclosed resources (files, connections, etc.)
- Inability to properly clean up in web applications
- No graceful shutdown capabilities
- Resource exhaustion in long-running applications

## Implementation Options

### Option 1: IDisposable Pattern
- Add `Disposable` protocol/interface
- Automatic disposal tracking and cleanup
- Pros: .NET-style familiar pattern, explicit control
- Cons: Requires user implementation, not automatic

### Option 2: Context Manager Integration
- Support for `__enter__`/`__exit__` methods
- Automatic cleanup via context management
- Pros: Pythonic, automatic resource management
- Cons: Requires context manager discipline

### Option 3: Lifecycle Hooks
- Hooks for creation, disposal, and cleanup phases
- Container-managed lifecycle
- Pros: Flexible, framework-managed
- Cons: More complex API

## Suggested Implementation Checklist

### Phase 1: Basic Disposal Support
- [ ] Add `Disposable` protocol with `dispose()` method
- [ ] Track disposable instances in container
- [ ] Implement `Container.dispose()` method to clean up all instances
- [ ] Add automatic disposal on container destruction

### Phase 2: Context Manager Integration
- [ ] Support instances that implement `__enter__`/`__exit__`
- [ ] Add `Container` context manager support
- [ ] Implement automatic resource cleanup on context exit
- [ ] Support nested container contexts

### Phase 3: Lifecycle Hooks
- [ ] Add `on_created` hook for post-instantiation setup
- [ ] Add `on_disposing` hook for pre-disposal cleanup
- [ ] Add `on_disposed` hook for post-disposal notifications
- [ ] Support async lifecycle hooks

### Phase 4: Advanced Lifecycle Features
- [ ] Implement dependency disposal ordering (dependents before dependencies)
- [ ] Add graceful vs forceful disposal modes
- [ ] Support for lifecycle timeouts
- [ ] Add lifecycle state tracking and inspection

### Phase 5: Framework Integration
- [ ] Integration with web framework request/response cycles
- [ ] Support for application shutdown hooks
- [ ] Background task lifecycle management
- [ ] Health check integration

## API Design Examples

### Basic Disposal:
```python
class DatabaseConnection(Disposable):
    def dispose(self):
        self.close()

with Container() as container:
    container.register(DatabaseConnection)
    db = container.get(DatabaseConnection)
    # db.dispose() called automatically on container exit
```

### Context Manager Support:
```python
@inject
def create_file_service() -> FileService:
    return FileService()  # Implements __enter__/__exit__

with container.get(FileService) as service:
    service.write_data("example")
# Automatic cleanup via __exit__
```

### Lifecycle Hooks:
```python
@container.add_lifecycle_hook("on_created", DatabaseConnection)
def setup_database(instance):
    instance.migrate_schema()

@container.add_lifecycle_hook("on_disposing", DatabaseConnection) 
def cleanup_database(instance):
    instance.rollback_transactions()
```

### Graceful Shutdown:
```python
container.dispose(timeout=30)  # 30 second graceful shutdown
container.force_dispose()      # Immediate cleanup
```

## Integration Considerations

### Web Applications:
- Request-scoped resource cleanup
- Connection pool management
- Session cleanup

### Background Services:
- Task cancellation and cleanup
- Resource pooling
- Periodic cleanup jobs

### Testing:
- Test isolation through cleanup
- Resource leak detection
- Mock disposal verification

## Technical Implementation Notes

### Disposal Order:
- Dispose dependents before their dependencies
- Build disposal dependency graph
- Handle circular dependencies gracefully

### Error Handling:
- Continue disposal even if some instances fail
- Collect and report disposal errors
- Timeout handling for stuck disposals

### Performance:
- Lazy disposal registration (only track disposables)
- Batch disposal for better performance
- Async disposal support

## Priority: High
Critical for production applications and proper resource management.

## Estimated Effort: High
Significant architectural changes but well-defined scope.