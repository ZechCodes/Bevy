# Type Annotation Support Enhancement

## Current State
- Basic support for type hints and `typing.Annotated`
- Simple type resolution with subclass checking
- Limited support for union types beyond `Type | None`

## Issues Identified
- [ ] No support for generic types like `List[Thing]`, `Dict[str, Thing]`
- [ ] Limited union type support beyond simple optional types
- [ ] No support for Protocol or ABC-based interfaces
- [ ] No support for `typing.Literal` or other advanced types
- [ ] Generic factory functions not supported

## Options for Enhancement

### Option 1: Full Typing Module Support
- Implement support for all `typing` module constructs
- Use `typing.get_origin()` and `typing.get_args()` for generics
- Pros: Complete type system support
- Cons: Complex implementation, potential performance impact

### Option 2: Gradual Enhancement
- Add support for most common generic types first
- Expand support incrementally based on user needs
- Pros: Manageable implementation, immediate value
- Cons: Incomplete coverage initially

### Option 3: Type Plugin System
- Create extensible type resolution system
- Allow users to register custom type handlers
- Pros: Flexible, user-extensible
- Cons: More complex API, higher learning curve

## Suggested Implementation Checklist

### Phase 1: Generic Collections
- [ ] Add support for `List[T]`, `Set[T]`, `Tuple[T, ...]`
- [ ] Add support for `Dict[K, V]`
- [ ] Implement generic type argument extraction
- [ ] Support nested generics like `List[Dict[str, Thing]]`

### Phase 2: Union and Optional Types
- [ ] Enhanced `Union[A, B, C]` support with fallback resolution
- [ ] Better `Optional[T]` handling with None injection
- [ ] Support for `Literal` types with value-based injection
- [ ] `Any` type support with runtime type checking

### Phase 3: Protocol and Interface Support
- [ ] Support `typing.Protocol` for structural typing
- [ ] Support `abc.ABC` abstract base classes
- [ ] Interface-based dependency resolution
- [ ] Multiple implementation support with qualifiers

### Phase 4: Advanced Types
- [ ] `Callable[[Args], RetVal]` support for function injection
- [ ] `ClassVar` and `Final` handling
- [ ] `TypeVar` and generic factory functions
- [ ] `NewType` support for type aliases

### Phase 5: Runtime Type Safety
- [ ] Optional runtime type checking for injected values
- [ ] Type validation in debug mode
- [ ] Generic constraint checking
- [ ] Better error messages for type mismatches

## Implementation Examples

### Generic Collections:
```python
@inject
def process_items(items: List[Item], lookup: Dict[str, Service]) -> None:
    # Container automatically resolves List[Item] and Dict[str, Service]
    pass
```

### Protocol Support:
```python
class StorageProtocol(Protocol):
    def save(self, data: str) -> None: ...

@inject
def backup_service(storage: StorageProtocol) -> BackupService:
    # Resolves any registered type implementing StorageProtocol
    return BackupService(storage)
```

### Union Types with Fallbacks:
```python
@inject
def service(cache: Union[RedisCache, MemoryCache]) -> MyService:
    # Tries RedisCache first, falls back to MemoryCache
    return MyService(cache)
```

## Technical Considerations

### Type Resolution Strategy
- Use `typing.get_origin()` and `typing.get_args()` for runtime introspection
- Implement type compatibility checking beyond simple `isinstance()`
- Cache type resolution results for performance

### Backward Compatibility
- Ensure existing type resolution continues to work
- Add feature flags for new type behaviors
- Gradual migration path for complex types

## Priority: Medium-High
Important for modern Python development and type safety.

## Estimated Effort: High
Requires significant changes to type resolution system and extensive testing.