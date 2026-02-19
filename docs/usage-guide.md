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
registry.add_factory(lambda container: Logger(container.get(Config)), Logger)
```

Key points:
- `get_registry()` returns the process-wide registry; configure it during startup.
- Register factories for types that need custom construction or expensive setup.
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
registry.add_factory(lambda container: TemplateService(cache_dir="/tmp"), TemplateService)
```

## 4. Invoke with `@auto_inject`

```python
from bevy import auto_inject

@auto_inject
@injectable
def send_welcome(user_id: str, notifier: Inject[Notifier]):
    notifier.send(user_id)
```

- Call `send_welcome(...)` directly and dependencies resolve from the global container.
- For alternate wiring, call `container.call(send_welcome, dependencies...)`; the calling container drives injection, while still honoring other decorators.

## 5. Use `Options` for Advanced Wiring

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

## 6. Embrace Hooks for Cross-Cutting Needs

The hook system lets you add tracing, caching, or guardrails without touching call sites. Hooks forward rich context so you can make informed decisions.

```python
from bevy.hooks import hooks
from tramp.optionals import Optional

@hooks.INJECTION_REQUEST
def log_request(container, injection_context):
    print(f"Injecting {injection_context.requested_type} for parameter {injection_context.parameter_name}")
    # Return Nothing to continue normal resolution
    return Optional.Nothing()

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


## 7. Common Patterns

- **Configuration modules**: group `container.add(...)` calls in one module and import it at startup.
- **Feature toggles**: register alternates on a branched container and pass it where needed.
- **Background jobs**: spin up a branch per job so overrides don't leak across tasks.
- **Tests**: branch, override dependencies, and dispose of the branch when the test ends.

## 8. Best Practices

- Keep container mutations in deterministic places (boot scripts, fixtures) to avoid hidden state.
- Avoid decorating the class object with `@injectable`; decorate callables (`__init__`, factories) so inheritance keeps working.
- Prefer `Inject[T]` annotations, even when using permissive strategies—this keeps types explicit.
- Use `InjectionStrategy.ANY_NOT_PASSED` sparingly; it's great for handlers but can hide missing dependencies.
- When layering decorators, apply `@auto_inject` closest to the function so wrappers don't block injection.

## 9. Troubleshooting Checklist

- **Missing dependency?** Ensure an instance or factory is registered on the container you’re calling with.
- **Unexpected instance?** Check for leftover overrides on a shared container—branch instead.
- **Double execution?** Wrapping decorators may run inner functions twice; ensure idempotency or move logic to injected services.

With these patterns, Bevy stays predictable across services, scripts, and tests while keeping injection setup minimal.
