# Factory vs Hook System Complexity

## Overview
Overlapping responsibilities between factories and hooks create confusion about when to use which approach.

## Current Complexity Issues
- Multiple ways to create instances (factories, hooks, type_factory)
- Unclear precedence and interaction between systems
- When to use which approach is not obvious
- Overlapping functionality with different APIs

## Why This Is Hard to Understand
- No clear separation of concerns
- Multiple entry points for similar functionality
- Complex interaction between hook types
- Different patterns for similar use cases

## Current Implementation Analysis

### Factories:
- Primary mechanism for instance creation
- Type-based registration
- Clean, straightforward API

### Hooks:
- `missing_injectable` - fallback when no factory found
- `post_injection_call` - modify instances after creation
- `factory_missing_type` - create factories dynamically
- `injection_request`/`injection_response` - intercept resolution

### Type Factory:
- Dynamic factory creation based on type inspection
- Automatic constructor injection
- Fallback mechanism

## Simplification Options

### Option 1: Clear Separation of Concerns
- Factories: Primary instance creation
- Hooks: Cross-cutting concerns (logging, validation, etc.)
- Clear guidelines on when to use each
- Pros: Maintains flexibility, clearer purpose
- Cons: Still multiple systems to learn

### Option 2: Unified API
- Single registration API with different strategies
- Hooks become internal implementation details
- Pros: Simpler external API
- Cons: Less flexibility for advanced users

### Option 3: Plugin Architecture
- Restructure as plugin system with clear interfaces
- Factories and hooks as different plugin types
- Pros: Extensible, clear boundaries
- Cons: More complex architecture

## Suggested Improvement Checklist

### Phase 1: Clear Documentation and Guidelines
- [ ] Document exact purpose of each system
- [ ] Create decision tree for factories vs hooks
- [ ] Add examples showing appropriate usage
- [ ] Document interaction and precedence rules

### Phase 2: API Consistency
- [ ] Consistent naming across factory and hook APIs
- [ ] Unified parameter patterns
- [ ] Clear error messages about conflicts
- [ ] Consistent return types and behaviors

### Phase 3: Simplified Common Cases
- [ ] Provide high-level APIs for common patterns
- [ ] Helper methods that choose appropriate mechanism
- [ ] Templates for typical use cases
- [ ] Migration utilities between approaches

### Phase 4: Advanced Use Cases
- [ ] Clear patterns for combining factories and hooks
- [ ] Advanced composition patterns
- [ ] Performance optimization guidelines
- [ ] Debugging tools for complex interactions

## Clear Usage Guidelines

### Use Factories When:
- Creating specific type instances
- Type has known dependencies
- Standard dependency injection patterns
- Performance is critical

### Use Hooks When:
- Cross-cutting concerns (logging, security, caching)
- Modifying behavior of existing factories
- Dynamic behavior based on context
- Framework integration points

### Use Type Factory When:
- Automatic registration of simple types
- Convention-based dependency injection
- Rapid prototyping
- Classes with straightforward constructors

## Simplified API Examples

### Current Confusing Patterns:
```python
# Too many ways to achieve similar results
container.register(UserService, factory=create_user_service)

@container.add_hook("missing_injectable")
def create_missing(container, requested_type):
    if requested_type == UserService:
        return create_user_service()

@container.add_hook("factory_missing_type") 
def create_factory(container, requested_type):
    if requested_type == UserService:
        return create_user_service
```

### Clearer Separation:
```python
# Primary registration - use factories
container.register(UserService, factory=create_user_service)

# Cross-cutting concerns - use hooks  
@container.add_hook("post_injection_call")
def add_logging(context):
    if isinstance(context.instance, UserService):
        context.instance.logger = get_logger()

# Fallback registration - clear purpose
container.register_fallback(UserService, factory=create_user_service)
```

### High-Level Helper APIs:
```python
# Simple registration with auto-detection
container.auto_register(UserService)  # Uses type_factory if no explicit factory

# Conditional registration
container.register_if(UserService, 
                     condition=lambda: env.get("ENABLE_USER_SERVICE"),
                     factory=create_user_service)

# Template-based registration
container.register_service_template(UserService, 
                                   with_logging=True,
                                   with_caching=True)
```

## Decision Matrix

| Goal | Mechanism | Example |
|------|-----------|---------|
| Create specific instance | Factory | `container.register(UserService, factory=create_user)` |
| Add logging to all services | Hook | `@container.add_hook("post_injection_call")` |
| Auto-wire simple classes | Type Factory | `container.enable_auto_wiring()` |
| Conditional creation | Factory with condition | `container.register_conditional(...)` |
| Modify existing behavior | Hook | `@container.add_hook("injection_response")` |
| Framework integration | Hook | `@container.add_hook("missing_injectable")` |

## Execution Order and Precedence

### Clear Resolution Order:
1. Explicit factory registration (highest priority)
2. Hook-based factory creation (`factory_missing_type`)
3. Type factory (automatic constructor injection)  
4. Missing injectable hook (fallback)
5. Error if nothing found

### Hook Execution Order:
1. `injection_request` - before resolution starts
2. Factory execution (or hook-based creation)
3. `post_injection_call` - after instance created
4. `injection_response` - before returning to caller

## Migration Strategy

### Identify Current Usage Patterns:
```python
# Audit tool to identify usage patterns
patterns = container.analyze_registration_patterns()
print(f"Direct factories: {patterns.direct_factories}")
print(f"Hook-based creation: {patterns.hook_factories}")
print(f"Overlapping registrations: {patterns.conflicts}")
```

### Provide Migration Helpers:
```python
# Convert hook-based factories to direct factories
container.convert_hook_factories_to_direct()

# Identify and resolve conflicts
conflicts = container.find_registration_conflicts()
for conflict in conflicts:
    print(f"Conflict: {conflict.type} registered via {conflict.mechanisms}")
```

## Performance Implications

### Optimization Guidelines:
- Direct factories are fastest (no hook overhead)
- Hooks add call overhead - use judiciously
- Type factory has reflection overhead
- Minimize hook count for performance-critical types

### Performance Monitoring:
```python
# Performance analysis
perf_report = container.get_performance_report()
print(f"Hook overhead: {perf_report.hook_overhead_ms}")
print(f"Factory performance: {perf_report.factory_performance}")
```

## Priority: Medium-High
Significant impact on developer experience and API clarity.

## Estimated Effort: Medium
Primarily documentation and API improvements with some refactoring.