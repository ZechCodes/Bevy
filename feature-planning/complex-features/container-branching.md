# Container Branching Complexity

## Overview
The parent-child container relationship and instance sharing behavior is confusing and poorly documented.

## Current Complexity Issues
- Unclear when to use branching vs creating new containers
- Confusing instance sharing behavior between parent/child
- No clear documentation on use cases
- Complex inheritance semantics
- Unpredictable resolution behavior

## Why This Is Hard to Understand
- Multiple ways to achieve similar results
- Implicit behavior not obvious from API
- Edge cases with singleton inheritance
- No clear mental model for developers

## Current Implementation Analysis
From `containers.py`, the branching system allows:
- Child containers inherit parent registrations
- Child can override parent registrations
- Instance sharing between parent/child is unclear

## Simplification Options

### Option 1: Clarify Existing API
- Better documentation with clear use cases
- Add examples for each branching scenario
- Explicit warnings about gotchas
- Pros: No breaking changes, immediate improvement
- Cons: Still complex underlying behavior

### Option 2: Simplified Branching Model
- Remove confusing edge cases
- Clear rules for inheritance and overrides
- Explicit instance sharing control
- Pros: Cleaner behavior, easier to understand
- Cons: Potential breaking changes

### Option 3: Remove Branching Feature
- Simplify to single container model
- Use composition instead of inheritance
- Pros: Much simpler, no confusion
- Cons: Breaking change, loss of functionality

## Suggested Improvement Checklist

### Phase 1: Documentation and Examples
- [ ] Document exact branching behavior with examples
- [ ] Create decision tree for when to use branching
- [ ] Add examples for common use cases (testing, scoping, etc.)
- [ ] Document instance sharing rules clearly

### Phase 2: API Clarification
- [ ] Add explicit parameters for inheritance behavior
- [ ] Rename methods to be more descriptive
- [ ] Add validation and warnings for complex scenarios
- [ ] Provide helper methods for common patterns

### Phase 3: Behavioral Improvements
- [ ] Make instance sharing explicit and configurable
- [ ] Add debugging info for resolution path (parent vs child)
- [ ] Implement clear override semantics
- [ ] Add validation for conflicting registrations

### Phase 4: Alternative Patterns
- [ ] Provide composition-based alternatives
- [ ] Add scoping as alternative to branching
- [ ] Create helper utilities for common branching patterns
- [ ] Migration guide from branching to other patterns

## Clarified API Examples

### Current Confusing Usage:
```python
parent = Container()
child = parent.branch()  # What does this inherit? What's shared?
# Unclear behavior
```

### Improved API:
```python
parent = Container() 
child = parent.create_child(
    inherit_singletons=True,    # Explicit singleton behavior
    inherit_registrations=True, # Explicit registration inheritance
    isolated_instances=False    # Explicit instance isolation
)

# Or even simpler factory methods:
test_container = parent.create_test_container()     # Clear purpose
scoped_container = parent.create_scoped_container() # Clear purpose
```

### Clear Use Case Examples:

#### Testing Scenario:
```python
# Production container
app_container = Container()
app_container.register(Database, factory=create_postgres_db)
app_container.register(EmailService, factory=create_smtp_email)

# Test container - override specific services  
test_container = app_container.create_test_container()
test_container.override(Database, factory=create_test_db)
test_container.override(EmailService, factory=create_mock_email)
# Inherits other registrations unchanged
```

#### Request Scoping Scenario:
```python
# Application container
app_container = Container()

# Request-scoped container
request_container = app_container.create_request_scope()
request_container.register_instance(CurrentUser, current_user)
request_container.register_instance(RequestId, request_id)
# Inherits application-level services, adds request-specific ones
```

## Decision Matrix for Container Usage

| Use Case | Solution | Rationale |
|----------|----------|-----------|
| Testing with mocks | `create_test_container()` | Override specific services |
| Request scoping | `create_request_scope()` | Add request-specific instances |
| Feature flags | `create_feature_container(flags)` | Conditional registrations |
| Tenant isolation | `create_tenant_container(tenant)` | Tenant-specific services |
| Plugin systems | `create_plugin_container()` | Isolated plugin dependencies |

## Simplified Mental Model

### Container Hierarchy:
```
Application Container (singletons, core services)
├── Request Container (request-specific instances)
│   ├── User Session Container (user-specific data)
│   └── Feature Container (feature-flagged services)
└── Test Container (mock implementations)
```

### Clear Rules:
1. Child containers inherit registrations from parents
2. Child registrations override parent registrations for same type
3. Instance sharing is explicit and configurable
4. Resolution always tries child first, then parent
5. Disposal cleans up child instances only

## Migration Strategy

### Phase 1: Maintain Compatibility
- Keep existing `branch()` method working
- Add new clear methods alongside existing ones
- Add deprecation warnings for confusing patterns

### Phase 2: Encourage Migration
- Documentation emphasizes new patterns
- Provide automated migration tools
- Add lint rules for old patterns

### Phase 3: Remove Complexity
- Remove confusing edge cases
- Simplify to clear, well-documented behavior
- Breaking change with clear migration path

## Performance Considerations
- Container hierarchy lookup performance
- Memory usage of parent references
- Resolution caching across container hierarchy

## Priority: High
This confusion significantly impacts developer experience.

## Estimated Effort: Medium
Mostly documentation and API improvements, some implementation changes.