# Async Hook Support Enhancement

## Overview
Extend the existing hook system to support asynchronous hook callbacks, ensuring consistent hook behavior between sync and async dependency resolution.

## Current Problem
The async dependency resolution implementation (completed) bypasses hooks for async factories, creating inconsistent behavior:

- ✅ **Sync factories**: Properly call all hooks (`GET_INSTANCE`, `CREATE_INSTANCE`, `CREATED_INSTANCE`, `GOT_INSTANCE`)
- ❌ **Async factories**: Bypass hooks entirely and cache instances directly
- ❌ **Mixed chains**: Inconsistent hook behavior between sync and async parts

## Impact
- Users cannot rely on hooks for debugging, logging, or custom behavior with async factories
- Breaks user expectations of consistent hook behavior
- Limits extensibility for async scenarios (async caching, logging, etc.)

## Goals
1. **Consistency**: All dependency resolution (sync/async) follows same hook patterns
2. **Backward Compatibility**: Existing sync hooks continue to work unchanged
3. **Extensibility**: Enable async hook patterns (redis caching, async logging, etc.)
4. **Performance**: Minimal overhead for sync-only scenarios

## Solution Design

### Phase 1: Core Async Hook Infrastructure (2-3 days)

#### 1.1 Extend HookManager for Async Support
**File**: `bevy/hooks.py`

**Tasks**:
- [ ] Add `handle_async()` method to `HookManager`
  - [ ] Support both sync and async callbacks
  - [ ] Return `Optional[Any]` with proper async handling
  - [ ] Maintain same first-wins behavior as sync version
- [ ] Add `filter_async()` method to `HookManager`
  - [ ] Chain async transformations properly
  - [ ] Support mixed sync/async callbacks
  - [ ] Preserve ordering and transformation semantics
- [ ] Add `AsyncHookFunction` type annotation
  - [ ] Support `Callable[[Container, Type[T]], T | Awaitable[T]]`
  - [ ] Update type hints throughout hook system

**Implementation Details**:
```python
async def handle_async[T](self, container: "Container", value: T) -> Optional[Any]:
    """Async version of handle() - calls first sync callback, then async callbacks."""
    # Call sync callbacks first (for backward compatibility)
    sync_result = self.handle(container, value)
    if sync_result != Optional.Nothing():
        return sync_result
    
    # Then try async callbacks
    for callback in self.async_callbacks:
        result = await callback(container, value)
        if isinstance(result, Optional) and result != Optional.Nothing():
            return result
    
    return Optional.Nothing()

async def filter_async[T](self, container: "Container", value: T) -> T:
    """Async version of filter() - applies all transformations sequentially."""
    # Apply sync filters first
    value = self.filter(container, value)
    
    # Then apply async filters
    for callback in self.async_callbacks:
        result = await callback(container, value)
        if isinstance(result, Optional) and result != Optional.Nothing():
            value = result.value
    
    return value
```

#### 1.2 Add Async Hook Registration
**File**: `bevy/registries.py`

**Tasks**:
- [ ] Add `add_async_hook()` method to `Registry`
- [ ] Update `HookManager` to track sync and async callbacks separately
- [ ] Ensure proper hook cleanup and management

#### 1.3 Create Async Instance Creation Methods
**File**: `bevy/containers.py`

**Tasks**:
- [ ] Add `_create_instance_async()` method
  - [ ] Mirror `_create_instance()` but with async hook support
  - [ ] Call `CREATE_INSTANCE` hook (async version)
  - [ ] Call factory (async or sync)
  - [ ] Call `CREATED_INSTANCE` hook (async version)
  - [ ] Cache instance properly
- [ ] Add `_get_instance_async()` helper
  - [ ] Call `GET_INSTANCE` hook (async version)
  - [ ] Fall back to instance creation if needed
  - [ ] Call `GOT_INSTANCE` hook (async version)

### Phase 2: Integration with Async Resolution (1-2 days)

#### 2.1 Update Async Dependency Resolution
**File**: `bevy/async_resolution.py`

**Tasks**:
- [ ] Replace direct factory calls with hook-aware creation
  - [ ] Change `instance = await factory(self.container)` 
  - [ ] To `instance = await self.container._create_instance_async(dep_type)`
- [ ] Ensure proper hook call sequence for all dependency types
- [ ] Add hook calls for both Phase 1 (async) and Phase 2 (sync in async context)

#### 2.2 Update Container.get() Async Path
**File**: `bevy/containers.py`

**Tasks**:
- [ ] Ensure async path calls hooks properly
- [ ] Update `DependenciesPending.get_result()` to use hook-aware methods
- [ ] Maintain consistency with sync hook behavior

### Phase 3: Testing and Documentation (2-3 days)

#### 3.1 Comprehensive Test Suite
**File**: `tests/test_async_hooks.py` (new)

**Test Categories**:
- [ ] **Basic Async Hook Functionality**
  - [ ] Async GET_INSTANCE hook with various return scenarios
  - [ ] Async CREATE_INSTANCE hook with factory override
  - [ ] Async CREATED_INSTANCE hook with instance transformation
  - [ ] Async GOT_INSTANCE hook with final processing
- [ ] **Mixed Sync/Async Hook Scenarios**
  - [ ] Sync hooks with async factories (backward compatibility)
  - [ ] Async hooks with sync factories (forward compatibility)
  - [ ] Mixed sync/async hooks on same dependency
  - [ ] Hook execution order (sync first, then async)
- [ ] **Hook Integration with Async Resolution**
  - [ ] Hooks called properly in async dependency chains
  - [ ] Hook behavior consistent between `container.get()` and `create_resolver()`
  - [ ] Parent container hook inheritance with async
  - [ ] Hook caching behavior with async instances
- [ ] **Error Handling and Edge Cases**
  - [ ] Async hook exceptions propagate properly
  - [ ] Hook timeouts don't break resolution
  - [ ] Circular dependencies with async hooks
  - [ ] Hook cleanup on container disposal
- [ ] **Performance Characteristics**
  - [ ] Sync-only paths not impacted by async hook infrastructure
  - [ ] Async hook overhead is reasonable
  - [ ] Hook execution doesn't block unnecessarily

#### 3.2 Integration Tests
**File**: `tests/test_async_resolution.py` (existing - update)

**Tasks**:
- [ ] Update existing async resolution tests to verify hook behavior
- [ ] Add hook-specific test cases to existing async scenarios
- [ ] Ensure no regression in async resolution functionality

#### 3.3 Documentation Updates
**Files**: `docs/` directory

**Tasks**:
- [ ] Update hook system documentation with async examples
- [ ] Add async hook patterns and best practices
- [ ] Document migration path for existing hook users
- [ ] Add troubleshooting guide for async hook issues

### Phase 4: Advanced Features (Optional - 1-2 days)

#### 4.1 Async Hook Utilities
**File**: `bevy/async_hooks.py` (new)

**Tasks**:
- [ ] Add common async hook patterns
  - [ ] `AsyncCacheHook` for Redis/external caching
  - [ ] `AsyncLoggingHook` for database logging
  - [ ] `AsyncMetricsHook` for performance monitoring
- [ ] Add hook composition utilities
- [ ] Add async hook debugging tools

#### 4.2 Hook Performance Optimizations
**Tasks**:
- [ ] Implement hook result caching where appropriate
- [ ] Add hook execution timeout configuration
- [ ] Optimize hook call overhead for high-frequency scenarios

## Implementation Checklist

### Pre-Implementation
- [ ] Review current hook usage patterns in codebase
- [ ] Identify all hook call sites that need async support
- [ ] Plan backward compatibility strategy
- [ ] Design async hook callback signature

### Phase 1: Core Infrastructure
- [ ] Extend `HookManager` with async methods
- [ ] Add async hook registration to `Registry`
- [ ] Create `_create_instance_async()` method
- [ ] Update type annotations for async hooks

### Phase 2: Integration
- [ ] Update `DependenciesPending._resolve_async_chain()`
- [ ] Replace direct factory calls with hook-aware creation
- [ ] Test async resolution hook integration
- [ ] Verify container inheritance works with async hooks

### Phase 3: Testing
- [ ] Write comprehensive async hook tests
- [ ] Update existing async resolution tests
- [ ] Performance testing for sync path impact
- [ ] Integration testing with real async scenarios

### Phase 4: Documentation
- [ ] Update API documentation
- [ ] Add async hook examples
- [ ] Create migration guide
- [ ] Document best practices

### Validation
- [ ] All existing tests pass (no regression)
- [ ] New async hook tests pass
- [ ] Performance benchmarks acceptable
- [ ] Documentation is complete and accurate

## Success Criteria

### Functional Requirements
1. **Hook Consistency**: All hooks work identically for sync and async dependencies
2. **Backward Compatibility**: Existing sync hooks continue to work without changes
3. **Async Support**: New async hooks can be registered and function properly
4. **Integration**: Async hooks work seamlessly with async dependency resolution

### Performance Requirements
1. **Sync Performance**: No measurable impact on sync-only dependency resolution
2. **Async Overhead**: Async hook overhead < 10% of async factory execution time
3. **Memory Usage**: Hook infrastructure memory overhead < 5% increase

### Quality Requirements
1. **Test Coverage**: >95% code coverage for new async hook functionality
2. **Documentation**: Complete API documentation and usage examples
3. **Error Handling**: Graceful handling of async hook failures
4. **Debugging**: Clear error messages and debugging support

## Timeline Estimate
- **Phase 1**: 2-3 days (Core infrastructure)
- **Phase 2**: 1-2 days (Integration)
- **Phase 3**: 2-3 days (Testing)
- **Phase 4**: 1-2 days (Documentation)
- **Total**: 6-10 days

## Priority
**High** - This addresses a significant functional gap in the async dependency resolution feature and ensures consistent user experience across sync/async scenarios.

## Dependencies
- Requires completed async dependency resolution feature ✅
- No external library dependencies
- Compatible with existing hook system

## Risks
1. **Complexity**: Adding async support to hooks increases system complexity
   - *Mitigation*: Thorough testing and clear documentation
2. **Performance**: Potential overhead for sync scenarios
   - *Mitigation*: Careful implementation with sync-first optimizations
3. **Breaking Changes**: Risk of unintended changes to existing hook behavior
   - *Mitigation*: Comprehensive backward compatibility testing

## Future Enhancements
- Hook composition and chaining
- Async hook timeouts and circuit breakers
- Hook performance monitoring and metrics
- Visual hook execution debugging tools