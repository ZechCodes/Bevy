# Error Handling Enhancement

## Current State
- Generic error messages like "No handler found that can handle dependency"
- Limited context about failed dependencies
- No stack trace or injection chain information
- Difficult to debug circular dependencies

## Issues Identified
- [ ] Error messages don't indicate which dependency failed
- [ ] No information about the injection chain leading to failure
- [ ] Circular dependency detection is basic or missing
- [ ] No differentiation between missing factory vs type mismatch
- [ ] Stack traces don't help identify injection source

## Options for Enhancement

### Option 1: Enhanced Exception Types
- Create specific exception classes for different failure modes
- Include dependency chain information in exceptions
- Pros: Clear categorization, better debugging
- Cons: Breaking change for existing error handling

### Option 2: Detailed Error Context
- Enhance existing exceptions with more context
- Add dependency resolution path tracking
- Pros: Backward compatible, immediate improvement
- Cons: Still using generic exception types

### Option 3: Debug Mode with Verbose Logging
- Add debug mode that logs injection attempts
- Maintain current error behavior for production
- Pros: Non-breaking, optional verbosity
- Cons: Debug information not always available when needed

## Suggested Implementation Checklist

### Phase 1: Exception Hierarchy
- [ ] Create `BevyError` base exception class
- [ ] Create `DependencyNotFoundError` with dependency info
- [ ] Create `CircularDependencyError` with cycle detection
- [ ] Create `TypeMismatchError` for type resolution failures
- [ ] Create `FactoryError` for factory execution failures

### Phase 2: Context Tracking
- [ ] Add dependency resolution path tracking in Container
- [ ] Include injection chain in all error messages
- [ ] Add source location information (file, line, function)
- [ ] Track factory/hook registration locations

### Phase 3: Circular Dependency Detection
- [ ] Implement proper cycle detection during resolution
- [ ] Show the complete circular path in error messages
- [ ] Add suggestions for breaking cycles
- [ ] Detect both direct and indirect cycles

### Phase 4: Debug and Diagnostic Tools
- [ ] Add `Container.debug_mode` flag
- [ ] Implement resolution logging when debug mode is enabled
- [ ] Add `Container.validate()` method to check for issues
- [ ] Create dependency graph visualization helper

### Phase 5: Error Recovery
- [ ] Add optional fallback mechanisms
- [ ] Implement graceful degradation options
- [ ] Add retry policies for transient failures
- [ ] Support for optional dependencies

## Example Enhanced Error Messages

### Before:
```
BevyError: No handler found that can handle dependency
```

### After:
```
DependencyNotFoundError: Cannot resolve dependency 'UserService' 
Injection chain: main() -> UserController.__init__() -> UserService
No factory registered for type 'UserService'
Registered types: AuthService, DatabaseConnection
Suggestion: Register UserService with @inject or container.register()
```

## Priority: High
Critical for developer experience and debugging.

## Estimated Effort: Medium
Requires changes to core resolution logic but well-scoped.