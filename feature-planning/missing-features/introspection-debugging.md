# Introspection and Debugging Tools

## Overview
Comprehensive tools for inspecting container state, visualizing dependencies, and debugging injection issues.

## Current Gap
- No tools for inspecting container state
- No dependency graph visualization
- No debug mode with injection logging
- No performance profiling tools
- Difficult to understand what's registered and how

## Why This Matters
- Debugging complex dependency issues
- Understanding application architecture
- Performance optimization
- Documentation and onboarding
- Preventing configuration mistakes

## Implementation Options

### Option 1: Built-in Debugging Tools
- Integrate debugging directly into core container
- Always-available inspection methods
- Pros: No additional dependencies, always consistent
- Cons: Adds complexity to core, potential performance impact

### Option 2: Separate Debug Package
- Optional debugging tools in separate module
- Import only when needed
- Pros: Clean separation, optional dependency
- Cons: May get out of sync with core

### Option 3: Plugin-Based Debugging
- Extensible debugging system via plugins
- Community can contribute specialized tools
- Pros: Extensible, specialized tools possible
- Cons: More complex architecture

## Suggested Implementation Checklist

### Phase 1: Basic Introspection
- [ ] Add `container.list_registrations()` method
- [ ] Implement `container.get_registration_info(type)` 
- [ ] Add factory source location tracking
- [ ] Support registration metadata and tags

### Phase 2: Dependency Graph
- [ ] Build dependency graph representation
- [ ] Add graph traversal and analysis methods
- [ ] Implement circular dependency detection
- [ ] Create text-based dependency tree display

### Phase 3: Debug Mode and Logging
- [ ] Add debug mode flag to container
- [ ] Implement detailed injection logging
- [ ] Add resolution path tracking
- [ ] Support injection performance timing

### Phase 4: Visualization Tools
- [ ] Generate DOT/Graphviz dependency graphs
- [ ] Create HTML interactive dependency explorer
- [ ] Add dependency graph export formats
- [ ] Implement graph layout algorithms

### Phase 5: Advanced Analysis
- [ ] Dependency usage analysis and optimization suggestions
- [ ] Unused registration detection
- [ ] Performance bottleneck identification
- [ ] Memory usage analysis for instances

## API Design Examples

### Basic Introspection:
```python
# List all registrations
for reg in container.list_registrations():
    print(f"{reg.type.__name__}: {reg.factory.__name__} ({reg.scope})")

# Get specific registration details
info = container.get_registration_info(UserService)
print(f"Factory: {info.factory}")
print(f"Dependencies: {info.dependencies}")
print(f"Registered at: {info.source_location}")
```

### Dependency Graph:
```python
# Get dependency graph
graph = container.get_dependency_graph()

# Find dependencies of a type
deps = graph.get_dependencies(UserService)
print(f"UserService depends on: {deps}")

# Find dependents of a type  
dependents = graph.get_dependents(Database)
print(f"Database is used by: {dependents}")

# Detect circular dependencies
cycles = graph.find_cycles()
if cycles:
    print(f"Circular dependencies found: {cycles}")
```

### Debug Mode:
```python
# Enable debug mode
container.debug_mode = True

# All injections will be logged
service = container.get(UserService)
# Output: 
# [DEBUG] Resolving UserService
# [DEBUG]   -> Resolving Database (dependency of UserService)
# [DEBUG]   <- Database resolved in 0.005s
# [DEBUG] <- UserService resolved in 0.012s
```

### Dependency Tree Visualization:
```python
# Print text dependency tree
container.print_dependency_tree(UserService)
# Output:
# UserService
# ├── Database
# │   └── ConfigService
# ├── CacheService
# │   └── ConfigService (shared)
# └── LoggerService

# Generate graphical visualization
container.export_dependency_graph("app_dependencies.png", format="png")
container.export_dependency_graph("app_dependencies.svg", format="svg")
```

### Interactive Inspector:
```python
# Launch web-based dependency explorer
container.start_inspector(port=8080)
# Opens browser with interactive dependency graph, registration details, etc.
```

## Advanced Analysis Features

### Performance Analysis:
```python
# Profile container performance
with container.performance_profiler():
    service = container.get(UserService)

# Get performance report
report = container.get_performance_report()
print(f"Slowest resolutions: {report.slowest_resolutions}")
print(f"Most expensive factories: {report.expensive_factories}")
```

### Usage Analysis:
```python
# Track dependency usage
container.enable_usage_tracking()

# After running application
usage_report = container.get_usage_report()
print(f"Unused registrations: {usage_report.unused}")
print(f"Most used dependencies: {usage_report.most_used}")
```

### Registration Validation:
```python
# Validate all registrations can be resolved
validation_result = container.validate_all()
if validation_result.errors:
    for error in validation_result.errors:
        print(f"Error: {error.type} - {error.message}")
```

## Debugging Workflow Examples

### Debugging Missing Dependency:
```python
try:
    service = container.get(UserService) 
except DependencyNotFoundError as e:
    # Enhanced error with debugging info
    print(f"Failed to resolve: {e.dependency}")
    print(f"Available registrations:")
    for reg in container.list_registrations():
        if "User" in reg.type.__name__:
            print(f"  - {reg.type.__name__}")
    
    # Suggest similar registrations
    suggestions = container.suggest_similar_types(e.dependency)
    print(f"Did you mean: {suggestions}")
```

### Debugging Circular Dependencies:
```python
# Detect and analyze cycles
cycles = container.get_dependency_graph().find_cycles()
for cycle in cycles:
    print(f"Circular dependency: {' -> '.join(cycle)}")
    print("Suggestions:")
    print("  - Use property injection instead of constructor injection")
    print("  - Introduce an interface to break the cycle")
    print("  - Use lazy injection with Provider<T>")
```

### Performance Debugging:
```python
# Find slow dependency resolutions
container.debug_mode = True
container.enable_performance_tracking()

# Run application
app.run()

# Analyze performance
report = container.get_performance_report()
for slow_resolution in report.slowest_resolutions:
    print(f"{slow_resolution.type}: {slow_resolution.time}ms")
    print(f"  Chain: {' -> '.join(slow_resolution.dependency_chain)}")
```

## Integration with Development Tools

### IDE Integration:
- Generate dependency diagrams for documentation
- Export registration information for IDE plugins
- Integration with debugger breakpoints

### CI/CD Integration:
- Dependency graph validation in build pipeline
- Performance regression detection
- Architecture compliance checking

### Documentation Generation:
- Auto-generate dependency documentation
- Create architecture decision records
- Generate onboarding guides

## Implementation Considerations

### Performance Impact:
- Debugging features should have minimal overhead when disabled
- Lazy collection of debugging information
- Optional detailed tracking

### Memory Usage:
- Careful memory management for graph storage
- Weak references where appropriate
- Configurable retention of debugging data

### Thread Safety:
- Thread-safe debugging information collection
- Concurrent access to introspection data
- Atomic operations for counters and metrics

## Priority: Medium
Very useful for development and debugging, but not critical for basic functionality.

## Estimated Effort: Medium-High
Comprehensive tooling requiring significant UI and visualization work.