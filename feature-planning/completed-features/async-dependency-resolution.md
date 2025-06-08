# Async Dependency Resolution

## Overview
Implement seamless async/await support for dependency injection that automatically detects when async resolution is needed and provides a unified API that works for both sync and async dependency chains.

## Why This Matters
- Modern Python applications are increasingly async (FastAPI, Starlette, aiohttp)
- Database connections, HTTP clients, and external services often require async initialization
- Current Bevy users must handle async dependencies manually outside the container
- Provides a competitive advantage over other DI frameworks

## Current Gap
- No support for async factory functions (`async def create_service()`)
- No automatic detection of async dependency chains
- Manual async handling required outside container
- Missing async context propagation for scoped dependencies

## Design Goals
1. **Zero Breaking Changes** - Existing sync code must continue working unchanged
2. **Automatic Detection** - No manual configuration of sync vs async
3. **Unified API** - Same `container.get()` method for both sync and async
4. **Type Safety** - Return type `T | Awaitable[T]` for proper IDE support
5. **Performance** - Sync-only chains should have zero async overhead

## Proposed Implementation

### Core API Changes

#### Container.get() Return Type
```python
def get(self, dependency_type: Type[T]) -> T | Awaitable[T]:
    """
    Get dependency instance. Returns:
    - T directly if all dependencies are synchronous
    - Awaitable[T] if any dependency requires async resolution
    """
    resolver = self.create_resolver(dependency_type)
    return resolver.get_result()
```

#### Container.create_resolver() Method
```python
def create_resolver(self, dependency_type: Type[T]) -> DependenciesReady | DependenciesPending:
    """
    Create resolver for dependency chain analysis.
    Returns DependenciesReady for sync chains, DependenciesPending for async chains.
    """
    chain_info = self._analyze_dependency_chain(dependency_type)
    
    if chain_info.has_async_factories:
        return DependenciesPending(self, dependency_type, chain_info)
    else:
        return DependenciesReady(self, dependency_type, chain_info)
```

### Resolver Classes

#### DependenciesReady
```python
class DependenciesReady:
    """Resolver for synchronous dependency chains"""
    
    def get_result(self) -> T:
        """Synchronously resolve and return the dependency instance"""
        return self._resolve_sync_chain()
```

#### DependenciesPending  
```python
class DependenciesPending:
    """Resolver for asynchronous dependency chains"""
    
    def get_result(self) -> Awaitable[T]:
        """Return coroutine that resolves the dependency instance"""
        return self._resolve_async_chain()
```

### Usage Examples

#### Automatic Async Detection
```python
# Sync factory
@injectable
def create_config() -> Config:
    return Config()

# Async factory  
@injectable
async def create_database(config: Config) -> Database:
    db = Database(config.db_url)
    await db.connect()
    return db

# Mixed dependency chain
@injectable
def create_user_service(db: Database) -> UserService:
    return UserService(db)

# Usage - same API, automatic behavior
config = container.get(Config)              # Returns Config (sync)
db = await container.get(Database)          # Returns coroutine (async)
service = await container.get(UserService)  # Returns coroutine (transitive async)
```

#### Framework Integration
```python
# FastAPI integration
@app.get("/users")
async def get_users(user_service: UserService = Depends(container.get)):
    return await user_service.get_all()

# Sync endpoint still works
@app.get("/config")  
def get_config(config: Config = Depends(container.get)):
    return config.to_dict()
```

## Implementation Checklist

### Phase 1: Foundation and Analysis (Week 1)
- [ ] **Test Setup**: Create comprehensive test suite structure
  - [ ] Test async factory registration and detection
  - [ ] Test mixed sync/async dependency chains  
  - [ ] Test error cases and edge conditions
  - [ ] Test performance of sync-only paths
  - [ ] Test circular dependency detection with async

- [ ] **Dependency Chain Analysis**: 
  - [ ] Implement `_analyze_dependency_chain()` method
  - [ ] Add async factory detection using `inspect.iscoroutinefunction()`
  - [ ] Build dependency graph traversal logic
  - [ ] Add caching for chain analysis results
  - [ ] Handle parent container inheritance in analysis

- [ ] **Chain Info Data Structure**:
  - [ ] Create `ChainInfo` class to store analysis results
  - [ ] Track which factories are async in the chain
  - [ ] Store dependency order for resolution
  - [ ] Include circular dependency detection

### Phase 2: Resolver Implementation (Week 2)
- [ ] **Base Resolver Classes**:
  - [ ] Implement `DependenciesReady` class
  - [ ] Implement `DependenciesPending` class  
  - [ ] Add proper type annotations and generic support
  - [ ] Implement resolver factory pattern

- [ ] **Sync Resolution Logic**:
  - [ ] Implement `DependenciesReady.get_result()` 
  - [ ] Integrate with existing sync resolution pipeline
  - [ ] Maintain hook system compatibility
  - [ ] Preserve caching behavior

- [ ] **Async Resolution Logic**:
  - [ ] Implement `DependenciesPending.get_result()` async method
  - [ ] Add concurrent resolution of independent async dependencies
  - [ ] Implement async hook execution pipeline
  - [ ] Handle async context propagation

### Phase 3: Container Integration (Week 3)
- [ ] **Container.create_resolver() Method**:
  - [ ] Implement resolver creation logic
  - [ ] Add dependency chain analysis integration
  - [ ] Handle caching and performance optimization
  - [ ] Add proper error handling and diagnostics

- [ ] **Container.get() Method Updates**:
  - [ ] Modify `get()` to use resolver pattern
  - [ ] Maintain backward compatibility
  - [ ] Add proper return type annotations
  - [ ] Preserve existing behavior for sync-only usage

- [ ] **Error Handling**:
  - [ ] Add helpful error messages for async/sync mismatches
  - [ ] Implement proper exception propagation in async chains
  - [ ] Add debugging information for resolution failures
  - [ ] Handle timeout scenarios for async resolution

### Phase 4: Hook System Integration (Week 4)  
- [ ] **Async Hook Support**:
  - [ ] Extend hook system to support async hook functions
  - [ ] Implement async hook execution pipeline
  - [ ] Add context passing for async resolution
  - [ ] Maintain hook ordering and priority

- [ ] **Hook Context Enhancement**:
  - [ ] Extend `InjectionContext` with async information
  - [ ] Add chain analysis results to context
  - [ ] Provide resolver type information to hooks
  - [ ] Support async context variables in hooks

### Phase 5: Testing and Validation (Week 5)
- [ ] **Comprehensive Test Coverage**:
  - [ ] Unit tests for all resolver classes
  - [ ] Integration tests for container methods
  - [ ] Performance tests comparing sync/async overhead  
  - [ ] Edge case testing (circular deps, complex chains)
  - [ ] Thread safety testing for async resolution

- [ ] **Framework Integration Tests**:
  - [ ] FastAPI integration testing
  - [ ] Basic async web framework compatibility
  - [ ] Performance benchmarks vs manual async handling
  - [ ] Memory usage analysis

### Phase 6: Documentation and Examples (Week 6)
- [ ] **API Documentation**:
  - [ ] Document new return types and signatures
  - [ ] Add type annotation examples
  - [ ] Document resolver classes and their usage
  - [ ] Add troubleshooting guide for async issues

- [ ] **User Guides**:
  - [ ] "Migrating to Async Dependencies" guide
  - [ ] "Async Dependency Best Practices" document
  - [ ] Framework integration examples and tutorials
  - [ ] Performance optimization guide

- [ ] **Code Examples**:
  - [ ] Simple async factory examples
  - [ ] Complex dependency chain examples  
  - [ ] Framework integration examples
  - [ ] Error handling and debugging examples

### Phase 7: Performance and Optimization (Week 7)
- [ ] **Performance Optimization**:
  - [ ] Cache dependency chain analysis results
  - [ ] Optimize sync-only path to avoid async overhead
  - [ ] Implement concurrent async dependency resolution
  - [ ] Add performance monitoring and metrics

- [ ] **Memory Management**:
  - [ ] Ensure proper cleanup of async resources
  - [ ] Implement async context manager support
  - [ ] Add memory leak detection for async chains
  - [ ] Optimize resolver object lifecycle

## Technical Considerations

### Backward Compatibility Strategy
- All existing sync code continues to work unchanged
- `container.get()` for sync-only dependencies returns objects directly
- No changes to existing `@injectable` decorator usage
- Existing hook system behavior preserved for sync chains

### Performance Requirements
- Sync-only dependency resolution should have zero async overhead
- Async chain analysis should be cached and reused
- Concurrent resolution of independent async dependencies
- Memory efficient resolver objects

### Error Handling Strategy
- Clear error messages when sync code tries to use async dependencies
- Proper exception propagation across async boundaries  
- Timeout handling for slow async factories
- Helpful debugging information for resolution failures

### Type Safety Requirements
- Proper return type annotations: `T | Awaitable[T]`
- Generic support for resolver classes
- IDE autocompletion and type checking support
- Static analysis compatibility

## Success Criteria

### Functional Requirements
- [ ] All existing sync dependency injection continues working unchanged
- [ ] Async factories can be registered and resolved automatically
- [ ] Mixed sync/async dependency chains resolve correctly
- [ ] Framework integration works seamlessly (FastAPI, etc.)

### Performance Requirements  
- [ ] Sync-only chains have <5% performance overhead
- [ ] Async chains resolve efficiently with concurrent dependency resolution
- [ ] Memory usage remains reasonable for complex dependency graphs
- [ ] Chain analysis caching provides significant performance benefit

### Quality Requirements
- [ ] >95% test coverage for all new functionality
- [ ] Comprehensive documentation with examples
- [ ] Zero breaking changes to existing API
- [ ] Clear error messages and debugging support

## Migration Strategy

### For Existing Users
- No immediate action required - existing code continues working
- Optional migration to async factories when beneficial
- Gradual adoption of async patterns supported

### For New Users  
- Choose sync or async factories based on dependencies
- Use same `container.get()` API regardless of choice
- Framework integration guides available

## Risk Assessment

### Low Risk
- Sync-only code path changes (well-tested existing behavior)
- Basic async factory support (straightforward extension)

### Medium Risk  
- Complex async dependency chains (requires thorough testing)
- Hook system integration with async (potential interaction issues)

### High Risk
- Performance impact on sync-only paths (requires careful optimization)
- Thread safety in async resolution (complex concurrency concerns)

## Timeline

**Total Estimated Duration: 7 weeks**

- **Weeks 1-2**: Foundation and core resolver implementation  
- **Weeks 3-4**: Container integration and hook system updates
- **Weeks 5-6**: Testing, documentation, and examples
- **Week 7**: Performance optimization and final polish

## Dependencies
- Python 3.8+ (for proper typing support)
- Existing Bevy architecture (containers, factories, hooks)
- asyncio standard library support