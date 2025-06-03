# Bevy 3.1.0-beta.2 Release 🚀

## 🌟 Major Features

### Enhanced Container.get() Method with Full Feature Parity
- **Unified Resolution Flow**: `container.get()` and `@inject` now use identical resolution logic
- **Default Factory Support**: Added `default_factory` parameter to `container.get()` method
- **Qualifier Support**: Full qualifier support in `container.get()` for feature parity with `Inject`
- **Container Inheritance**: Fixed function injection to properly traverse parent containers

## 🔧 Technical Improvements

### Dependency Resolution
- **Factory-Based Caching**: Factory functions now used as cache keys for consistent behavior
- **Parent Container Traversal**: Both `container.get()` and function injection check parent containers
- **Precedence Rules**: Default factories take precedence over existing instances when explicitly specified

### Developer Experience
- **GitHub Actions Automation**: Complete release automation with PyPI trusted publisher
- **Development Documentation**: Added comprehensive CLAUDE.md with release procedures
- **Workflow Standardization**: Consistent `.yaml` extension for all GitHub Actions workflows

## 📚 Documentation Updates

- **Release Automation Guide**: Complete documentation for automated releases
- **Development Procedures**: Step-by-step release and testing procedures
- **Architecture Documentation**: Detailed explanation of container inheritance and caching

## 🧪 Testing & Quality

### Test Coverage
- **Comprehensive Test Suite**: Added `test_container_get_comprehensive.py` for `container.get()` behavior
- **Qualifier Testing**: New `test_container_get_qualifiers.py` for qualifier functionality
- **Behavior Parity**: Tests verify identical behavior between `container.get()` and `@inject`

## 💡 Usage Examples

### Enhanced Container.get() with Default Factory:
```python
from bevy import Container, Inject

container = Container()

# Using default factory with container.get()
def create_service():
    return MyService("configured")

# Default factory takes precedence over existing instances
service = container.get(MyService, default_factory=create_service)

# Identical behavior with qualifiers
qualified_service = container.get(MyService, qualifier="special", default_factory=create_service)
```

## 🔄 Migration Guide

No breaking changes in this release. All existing code continues to work unchanged.

## ⚠️ Breaking Changes

None in this pre-release.

## 🐛 Bug Fixes

- Fixed function injection container traversal for parent container inheritance
- Resolved default factory precedence handling in dependency resolution
- Enhanced exception propagation in container.get() method

## 🙏 Acknowledgments

Thank you to all contributors who made this release possible!

---

**Full Changelog**: [View on GitHub](https://github.com/ZechCodes/Bevy/compare/v[PREVIOUS_VERSION]...v3.1.0-beta.2)

**Installation**: `pip install bevy==3.1.0-b.2`

**Feedback**: Please report any issues or feedback on our [GitHub Issues](https://github.com/ZechCodes/Bevy/issues) page.
