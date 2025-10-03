# Bevy Usage Guide

This guide highlights the core workflows in Bevy 3.1, plus patterns and practices to keep your projects maintainable.

## 1. Configure the Registry

Use the shared registry to declare factories and hooks *before* any containers exist. Pull it once and keep configuration in dedicated modules so every container shares the same wiring.

```python
from bevy import get_registry
from bevy.hooks import hooks

registry = get_registry()

# Register hook callbacks
@hooks.CREATE_INSTANCE
def audit_creation(container, dependency, context):
    ...

audit_creation.register_hook(registry)
registry.add_factory(Logger, lambda container: Logger(container.get(Config)))
```

Key points:
- `get_registry()` returns the process-wide registry; configure it during startup.
- Register factories for types that need custom construction or expensive setup.
- Factories can be sync or async functions - async factories are properly awaited.
- Register hooks before containers to keep observability and overrides consistent everywhere.

## 2. Establish a Container

```python
from bevy import get_container

container = get_container()  # global singleton
branch = container.branch()  # isolated container for tests/tasks
```

Keep one global container for production code. Use `Container.branch()` for request handling, tests, or any workflow that needs isolated overrides.

## 3. Register Dependencies Intentionally

```python
from bevy import injectable, Inject

class EmailService: ...
class TemplateService: ...

class Notifier:
    @injectable
    def __init__(
        self,
        email: Inject[EmailService],
        templates: Inject[TemplateService],
    ):
        self.email = email
        self.templates = templates
```

- Decorate constructor-style callables (`__init__`, factory functions) so the class itself stays a normal `type` for inheritance.
- Register instances explicitly when they have runtime data:

```python
container.add(EmailService, EmailService())
container.add(TemplateService, TemplateService(cache_dir="/tmp"))
```

- Register factories on the registry for types that need custom construction:

```python
# Sync factory
registry.add_factory(TemplateService, lambda container: TemplateService(cache_dir="/tmp"))

# Async factory - properly awaited during resolution
async def create_database(container):
    config = container.get(Config)
    db = Database(config.db_url)
    await db.connect()
    return db

registry.add_factory(create_database, Database)
```

## 4. Invoke with `@auto_inject`

```python
from bevy import auto_inject

@auto_inject
@injectable
async def send_welcome(user_id: str, notifier: Inject[Notifier]):
    await notifier.send(user_id)
```

- Call `send_welcome(...)` directly and dependencies resolve from the global container.
- For alternate wiring, call `container.call(send_welcome, dependencies...)`; the calling container drives injection, while still honoring other decorators.

## 5. Async-Native Dependency Resolution

Bevy is built async-first. For async code, use `container.find()` which returns a `Result` that can be resolved in either sync or async contexts.

### Using `find()` in Async Code

```python
# ✅ Best practice: Use find() in async code
async def process_order(order_id: str):
    db = await container.find(Database)
    cache = await container.find(Cache, qualifier="redis")
    config = await container.find(Config, default_factory=load_default_config)

    # Your async logic here
    await db.save(order_id)
```

### Async Function Injection

Async functions decorated with `@injectable` work seamlessly with `container.call()`:

```python
@injectable
async def send_notification(
    user_id: str,
    email: Inject[EmailService],
    db: Inject[Database]
):
    user = await db.get_user(user_id)
    await email.send(user.email, "Welcome!")

# Call it - returns a coroutine
await container.call(send_notification, user_id="123")
```

### The `Result` Type

`container.find()` returns a `Result[T]` that can be resolved in multiple ways:

```python
result = container.find(Service)

# Async context - truly async resolution with no thread overhead
instance = await result  # Uses __await__
# OR
instance = await result.get_async()

# Sync context - runs async resolution in a thread
instance = result.get()

# Sync container.get() - shorthand for find().get()
instance = container.get(Service)
```

### Why `find()` Instead of `get()` in Async Code?

```python
# ❌ Avoid: get() in async code creates thread overhead
async def bad_example():
    service = container.get(Service)  # Spawns thread + event loop
    await service.do_work()

# ✅ Better: find() in async code stays truly async
async def good_example():
    service = await container.find(Service)  # No thread overhead
    await service.do_work()
```

**Key differences:**
- `container.get(T)` → Sync operation, runs async hooks in isolated threads
- `await container.find(T)` → Async operation, runs async hooks in same async context
- Async hooks can do real async work (I/O, delays) when using `find()`
- Dependencies injected into async functions use `find()` automatically

### Options Work the Same

All `Options` work with both `find()` and `get()`:

```python
# Qualified dependencies
primary_db = await container.find(Database, qualifier="primary")

# Default factories
config = await container.find(Config, default_factory=load_config)

# Non-cached factory calls
logger = await container.find(Logger,
    default_factory=create_logger,
    cache_factory_result=False
)
```

## 6. Use `Options` for Advanced Wiring

```python
from bevy import Options

@injectable
def build_report(
    primary_db: Inject[Database, Options(qualifier="primary")],
    backup_db: Inject[Database, Options(qualifier="backup")],
    config: Inject[Config, Options(default_factory=load_config)],
): ...
```

- **Qualifiers** let you keep multiple variants of the same type.
- **`default_factory`** fills gaps when no instance is registered.
- **`optional=True`** or `Inject[Thing | None]` handles soft dependencies gracefully.

## 7. Embrace Hooks for Cross-Cutting Needs

The async-aware hook system lets you add tracing, caching, or guardrails without touching call sites. Hooks accept sync or async callbacks and forward rich context so you can make informed decisions.

```python
from bevy.hooks import hooks

@hooks.INJECTION_REQUEST
def log_request(container, context):
    container.logger.info("Injecting %s", context.requested_type)

log_request.register_hook(container.registry)
```

### Hook Reference at a Glance

| Hook | When it fires | Value argument | Expected return | Notable context keys |
| --- | --- | --- | --- | --- |
| `GET_INSTANCE` | Before the container returns something from `.get()` or `.find()` | Requested type | `Optional.Some(instance)` to short-circuit resolution; `Optional.Nothing()` to continue | `injection_context` (when called from injection), plus anything you passed to `Container.get(context=...)` |
| `GOT_INSTANCE` | After an instance is fetched and before caching | Resolved instance | `Optional.Some(new_instance)` to rewrite before caching; `Optional.Nothing()` keeps the original | Same as above |
| `CREATE_INSTANCE` | Just before Bevy tries registered factories | Requested type | `Optional.Some(instance)` to provide/custom-cache; `Optional.Nothing()` lets Bevy try factories | `injection_context` |
| `CREATED_INSTANCE` | Immediately after a factory-built instance is created | Newly created instance | `Optional.Some(new_instance)` to wrap/modify; `Optional.Nothing()` leaves it unchanged | Same as above |
| `HANDLE_UNSUPPORTED_DEPENDENCY` | When no factory can create the type | Requested type | `Optional.Some(fallback)` to recover; `Optional.Nothing()` raises `DependencyResolutionError` | `injection_context` |
| `INJECTION_REQUEST` | Before resolving a dependency for injection | `InjectionContext` with parameter info | `Optional.Some(instance)` to provide value directly; `Optional.Nothing()` to continue resolution | `injection_context` includes function name, parameter name, requested type, defaults |
| `INJECTION_RESPONSE` | After resolving a dependency for injection | Resolved instance | `Optional.Some(new_instance)` to transform; `Optional.Nothing()` keeps original | Same as above |

Returning `Optional.Nothing()` (or simply `None` for legacy two-argument hooks) signals "no change, continue the default flow."

Hooks are fully async-aware and can be either sync or async functions. When using `await container.find(T)`, async hooks execute in the same async context with no thread overhead.

## 8. Common Patterns

- **Configuration modules**: group `container.add(...)` calls in one module and import it at startup.
- **Feature toggles**: register alternates on a branched container and pass it where needed.
- **Background jobs**: spin up a branch per job so overrides don't leak across tasks.
- **Tests**: branch, override dependencies, and dispose of the branch when the test ends.

## 9. Best Practices

- Keep container mutations in deterministic places (boot scripts, fixtures) to avoid hidden state.
- Avoid decorating the class object with `@injectable`; decorate callables (`__init__`, factories) so inheritance keeps working.
- Prefer `Inject[T]` annotations, even when using permissive strategies—this keeps types explicit.
- Use `InjectionStrategy.ANY_NOT_PASSED` sparingly; it's great for handlers but can hide missing dependencies.
- When layering decorators, apply `@auto_inject` closest to the function so wrappers don't block injection.
- Leverage async hooks to observe long-running workflows; avoid side effects inside hooks that could raise errors.
- **In async code, use `await container.find(T)` instead of `container.get(T)`** to avoid unnecessary thread overhead.

## 10. Troubleshooting Checklist

- **Missing dependency?** Ensure an instance or factory is registered on the container you’re calling with.
- **Unexpected instance?** Check for leftover overrides on a shared container—branch instead.
- **Double execution?** Wrapping decorators may run inner functions twice; ensure idempotency or move logic to injected services.

With these patterns, Bevy stays predictable across services, scripts, async workers, and tests while keeping injection setup minimal.
