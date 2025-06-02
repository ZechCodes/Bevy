# Hook System Enhancement

## Current State
- Five hook types: missing_injectable, post_injection_call, factory_missing_type, injection_request, injection_response
- Basic hook registration and execution
- No ordering or priority system
- Hooks cannot be removed once registered

## Issues Identified
- [ ] No hook ordering or priority system for deterministic execution
- [ ] Cannot remove or disable hooks after registration
- [ ] Limited hook lifecycle (no pre-injection hooks for all cases)
- [ ] Hook debugging is difficult
- [ ] No hook metadata or introspection capabilities

## Options for Enhancement

### Option 1: Priority-Based Hook System
- Add priority/weight system for hook ordering
- Allow hook removal and dynamic management
- Pros: Deterministic behavior, flexible management
- Cons: Added complexity for simple use cases

### Option 2: Event-Driven Hook System
- Restructure as event system with more granular events
- Support event filtering and conditional hooks
- Pros: More flexible, better separation of concerns
- Cons: Breaking change, more complex API

### Option 3: Layered Enhancement
- Keep existing API, add priority and management features
- Extend with new hook types as needed
- Pros: Backward compatible, incremental improvement
- Cons: May lead to inconsistent API over time

## Suggested Implementation Checklist

### Phase 1: Hook Management
- [ ] Add hook priority/weight system (0-100 scale)
- [ ] Implement `container.remove_hook()` method
- [ ] Add `container.disable_hook()` / `enable_hook()` methods
- [ ] Support hook tagging/grouping for batch operations

### Phase 2: Extended Hook Lifecycle
- [ ] Add `pre_injection` hook for all dependency requests
- [ ] Add `post_factory_creation` hook after factory execution
- [ ] Add `container_created` and `container_destroyed` hooks
- [ ] Add `dependency_cached` hook for singleton creation

### Phase 3: Hook Context and Metadata
- [ ] Provide rich context object to hooks with injection chain
- [ ] Add hook registration metadata (name, description, tags)
- [ ] Support conditional hooks with predicate functions
- [ ] Add hook execution timing and performance metrics

### Phase 4: Hook Debugging and Introspection
- [ ] Add `container.list_hooks()` method with details
- [ ] Implement hook execution logging in debug mode
- [ ] Add hook execution order visualization
- [ ] Support hook performance profiling

### Phase 5: Advanced Hook Features
- [ ] Async hook support for async dependency resolution
- [ ] Hook composition and chaining mechanisms
- [ ] Hook templates for common patterns
- [ ] Plugin system built on hooks

## Enhanced Hook API Examples

### Priority-Based Hooks:
```python
@container.add_hook("injection_request", priority=10, name="auth_check")
def check_authentication(context):
    # Runs before lower priority hooks
    pass

@container.add_hook("injection_request", priority=5, name="logging")  
def log_request(context):
    # Runs after auth_check
    pass
```

### Hook Management:
```python
# Remove specific hook
container.remove_hook("injection_request", "auth_check")

# Disable all hooks with tag
container.disable_hooks(tag="debug")

# List all hooks
for hook in container.list_hooks():
    print(f"{hook.name}: {hook.priority} ({hook.status})")
```

### Rich Context:
```python
@container.add_hook("injection_request")
def debug_hook(context):
    print(f"Resolving {context.requested_type}")
    print(f"Injection chain: {' -> '.join(context.injection_chain)}")
    print(f"Source: {context.source_file}:{context.source_line}")
```

### Conditional Hooks:
```python
@container.add_hook("post_injection_call", 
                   condition=lambda ctx: ctx.instance_type == UserService)
def user_service_hook(context):
    # Only runs for UserService instances
    pass
```

## Performance Considerations
- Hook execution should be optimized for common cases
- Consider hook compilation/caching for frequently used patterns
- Provide option to disable hooks entirely for production

## Migration Strategy
- Keep existing hook API unchanged
- Add new features as optional parameters
- Provide migration utilities for complex hook setups

## Priority: Medium
Useful for advanced users but not critical for basic functionality.

## Estimated Effort: Medium
Well-scoped enhancement to existing system.