# Bevy 3.1.0-beta.1 Release 🚀

We're excited to announce the release of Bevy 3.1.0-beta.1, featuring a major overhaul of the dependency injection system with modern Python 3.12+ features and significant new functionality!

## 🌟 Major Features

### Factory-Based Caching System
- **Intelligent Caching**: Factory functions now serve as cache keys, ensuring same factory = same instance
- **Configurable Behavior**: Control caching with `cache_factory_result` parameter in `Options` class
- **Performance Optimization**: Eliminates redundant factory calls while maintaining flexibility for testing scenarios
- **Unified Architecture**: Merged factory cache into main instances cache for simplified container management

### Modern Type System Overhaul
- **Python 3.12+ Type Alias**: Replaced `dependency()` with clean `Inject[T]` syntax
- **Rich Options Support**: Enhanced `Options` class with factory caching controls
- **Type-Safe Annotations**: Full IDE support with modern Python type hints
- **Qualified Dependencies**: Support for multiple implementations with string qualifiers

## 🔧 Technical Improvements

### Enhanced Container System
- **Unified Cache Architecture**: Single instances cache supporting Type, (Type, qualifier), and Callable keys
- **Parent Container Inheritance**: Factory cache properly inherited across container branches
- **Improved Error Handling**: Better error messages with proper context and parameter names
- **Thread Safety Improvements**: Enhanced concurrent access patterns

### Developer Experience
- **Comprehensive Documentation**: Updated API docs, guides, and quickstart for 3.1 features
- **Rich Hook Context**: Enhanced injection hooks with detailed execution context
- **Better Debugging**: Improved debug logging and error reporting
- **Modern Syntax**: Clean, readable dependency injection patterns

## 📚 Documentation Updates

- **Complete API Documentation**: Updated for all new 3.1 features
- **Enhanced Quickstart Guide**: Added factory caching examples and best practices
- **Migration Examples**: Clear examples showing 3.0 → 3.1 syntax changes
- **Comprehensive Guides**: Updated index and navigation structure

## 🧪 Testing & Quality

### Reorganized Test Suite
- **Focused Test Files**: Split generic tests into meaningful, descriptive test files:
  - `test_factory_caching.py` - Factory caching functionality
  - `test_type_resolution.py` - Complex type scenarios
  - `test_error_handling.py` - Error handling validation
  - `test_container_branching.py` - Container inheritance scenarios
  - `test_concurrency.py` - Thread safety and concurrent access
  - `test_performance.py` - Performance with large dependency graphs

### Enhanced Coverage
- **111 Passing Tests**: Comprehensive test coverage including edge cases
- **Performance Testing**: Large dependency graph validation
- **Concurrency Testing**: Basic thread safety scenarios
- **Error Scenario Validation**: Comprehensive error handling coverage

## 💡 Usage Examples

### Before (3.0):
```python
from bevy import dependency

@auto_inject
def process_data(
    service: UserService = dependency(),
    logger: Logger = dependency(default_factory=lambda: Logger("app"))
):
    return service.process()
```

### After (3.1):
```python
from bevy import injectable, auto_inject, Inject
from bevy.injection_types import Options

@auto_inject
@injectable
def process_data(
    service: Inject[UserService],
    logger: Inject[Logger, Options(default_factory=lambda: Logger("app"))]
):
    return service.process()
```

### Factory Caching:
```python
@injectable
def create_expensive_service() -> DatabaseService:
    return DatabaseService(connect_to_database())

@injectable  
def handler_a(service: Inject[DatabaseService, Options(default_factory=create_expensive_service)]):
    return service.query("SELECT * FROM users")

@injectable
def handler_b(service: Inject[DatabaseService, Options(default_factory=create_expensive_service)]):
    return service.query("SELECT * FROM products")

# Both handlers share the same DatabaseService instance!
```

### Qualified Dependencies:
```python
container.add(Database, DatabaseConnection("primary"), qualifier="primary")
container.add(Database, DatabaseConnection("backup"), qualifier="backup")

@injectable
def data_processor(
    primary_db: Inject[Database, Options(qualifier="primary")],
    backup_db: Inject[Database, Options(qualifier="backup")]
):
    return f"Using {primary_db.name} with {backup_db.name} backup"
```

## 🔄 Migration Guide

1. **Update Imports**: Replace `dependency()` imports with `Inject` and `Options`
2. **Update Syntax**: Convert `param = dependency()` to `param: Inject[Type]`
3. **Factory Options**: Use `Options(default_factory=func)` instead of `dependency(default_factory=func)`
4. **Decorator Order**: Ensure `@injectable` comes after `@auto_inject` if using both

## ⚠️ Breaking Changes

- **Removed**: `dependency()` function (replaced with `Inject[T]` syntax)
- **Removed**: `from_config` parameter in Options class
- **Changed**: Decorator configuration now uses modern `@injectable` decorator
- **Required**: Python 3.12+ for full type alias support

## 🐛 Bug Fixes

- Fixed UnionType error handling in dependency resolution
- Improved container branching inheritance behavior
- Enhanced thread safety in concurrent scenarios
- Better error messages for missing qualified dependencies

## 🙏 Acknowledgments

This release represents a significant modernization of Bevy's dependency injection system, bringing it in line with current Python best practices while maintaining the simplicity and power that makes Bevy great.

---

**Full Changelog**: [View on GitHub](https://github.com/ZechCodes/Bevy/compare/v3.0.0...v3.1.0-beta.1)

**Installation**: `pip install bevy==3.1.0b1`

**Feedback**: Please report any issues or feedback on our [GitHub Issues](https://github.com/ZechCodes/Bevy/issues) page.