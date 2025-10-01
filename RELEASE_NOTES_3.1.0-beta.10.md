# Bevy 3.1.0-beta.10 Release 🚀

## 🌟 Major Features

### Async-Native Dependency Resolution with `find()` and `Result`
- **New `container.find()` method**: Returns a `Result[T]` type that can be resolved in sync or async contexts
- **`Result` type**: Deferred dependency resolution with `.get()` (sync) and `.get_async()` (async) methods
- **Benefit**: Truly async-native dependency resolution with no thread overhead in async code

### Async Function Injection
- **Automatic async detection**: `@injectable` async functions work seamlessly with `container.call()`
- **Async-native injection**: Dependencies are resolved using `await container.find()` automatically
- **Benefit**: Write async functions with dependency injection just like sync functions

### Async-Native Hook Architecture
- **Removed sync wrappers**: Hooks now execute in native async context when using `find()`
- **Real async work**: Async hooks can perform I/O, delays, and other async operations efficiently
- **Benefit**: No unnecessary thread spawning when working in async contexts

## 🔧 Technical Improvements

### Hook System
- **Async-first execution**: `HookManager.handle()` and `HookManager.filter()` are now purely async
- **Sync compatibility**: Sync hooks still work - automatically called within async context
- **Pattern matching**: Use match/case instead of isinstance for Optional checks

### Container API
- **Read-only `parent` property**: Clean API for accessing parent containers
- **Removed dead code**: Cleaned up unused `_create_instance` and `_call_post_injection_hook` methods

## 📚 Documentation Updates

- **New Section**: "Async-Native Dependency Resolution" in usage guide with best practices
- **API Reference**: Complete documentation for `Result` type and `find()` method
- **Hook Reference**: Updated to clarify which hooks work in async-native architecture
- **Best Practices**: Added guidance on using `await container.find(T)` instead of `container.get(T)` in async code

## 🧪 Testing & Quality

### Test Coverage
- **7 new async function injection tests**: Covering async functions with hooks, qualifiers, and factories
- **Async hook verification**: Tests confirm async hooks run in same async context (no thread overhead)
- **Total**: 179 tests passing (up from 172)

## 💡 Usage Examples

### Async-Native Dependency Resolution:
```python
from bevy import injectable, Inject, get_container

# In async code - truly async with no thread overhead
async def process_order(order_id: str):
    container = get_container()
    db = await container.find(Database)
    cache = await container.find(Cache, qualifier="redis")

    user = await db.get_user(order_id)
    await cache.set(f"user:{order_id}", user)

# Async function injection
@injectable
async def send_notification(
    user_id: str,
    email: Inject[EmailService],
    db: Inject[Database]
):
    user = await db.get_user(user_id)
    await email.send(user.email, "Welcome!")

# Call it - returns a coroutine
container = get_container()
await container.call(send_notification, user_id="123")
```

### Result Type:
```python
# Get a Result for deferred resolution
result = container.find(Service)

# Resolve in async context - no thread overhead
instance = await result  # Uses __await__
# OR
instance = await result.get_async()

# Resolve in sync context - runs async in thread
instance = result.get()
```

## ⚠️ Breaking Changes

### Injection Lifecycle Hooks (Minor Impact)
The following hooks are **no longer called** from sync `container.call()` in the async-native architecture:
- `INJECTION_REQUEST`
- `INJECTION_RESPONSE`
- `POST_INJECTION_CALL`
- `MISSING_INJECTABLE`
- `FACTORY_MISSING_TYPE`

**Migration**: Use dependency resolution hooks instead (`GET_INSTANCE`, `GOT_INSTANCE`, `CREATE_INSTANCE`, `CREATED_INSTANCE`, `HANDLE_UNSUPPORTED_DEPENDENCY`), which work in both sync and async contexts.

**Impact**: Low - these hooks were primarily used for observability, and most users don't use them.

## 🙏 Acknowledgments

Thank you to all contributors who made this release possible!

---

**Full Changelog**: [View on GitHub](https://github.com/ZechCodes/Bevy/compare/v3.1.0-beta.9...v3.1.0-beta.10)

**Installation**: `pip install bevy==3.1.0-beta.10`

**Feedback**: Please report any issues or feedback on our [GitHub Issues](https://github.com/ZechCodes/Bevy/issues) page.
