# Container Branching Guide

Container branching is one of Bevy's most powerful features for managing dependencies across different contexts like testing, request handling, and environment configurations. This guide explains how to use container branching effectively.

## What is Container Branching?

Container branching creates a parent-child relationship between containers where:
- **Child containers inherit** all instances from their parent
- **Child containers can override** parent instances without affecting the parent
- **Sibling containers are isolated** from each other's changes
- **Resolution walks up** the container hierarchy (child → parent → grandparent)

## Core Inheritance Rules

### 1. Inheritance
```python
from bevy import Container, Registry

registry = Registry()
parent = Container(registry)
parent.add(DatabaseConnection("parent-db"))

child = parent.branch()
# Child can access parent's database
db = child.get(DatabaseConnection)  # Returns "parent-db"
```

### 2. Override Isolation
```python
# Child overrides don't affect parent
child.add(DatabaseConnection("child-db"))  # Override parent's DB

child_db = child.get(DatabaseConnection)    # Returns "child-db"
parent_db = parent.get(DatabaseConnection)  # Still returns "parent-db"
```

### 3. Sibling Isolation
```python
# Siblings don't affect each other
sibling1 = parent.branch()
sibling1.add(EmailService("sibling1-email"))

sibling2 = parent.branch() 
sibling2.add(CacheService("sibling2-cache"))

# sibling1 cannot access sibling2's cache service
# sibling2 cannot access sibling1's email service
# Both can access parent's database
```

### 4. Factory Cache Inheritance
```python
from bevy import inject, Inject, Options

@inject
def expensive_service_factory():
    # Expensive creation logic
    return ExpensiveService()

# Parent creates and caches the instance
parent_service = parent.get(ExpensiveService, default_factory=expensive_service_factory)

# Child inherits the cached instance (no re-creation)
child = parent.branch()
child_service = child.get(ExpensiveService, default_factory=expensive_service_factory)

assert parent_service is child_service  # Same instance
```

## Common Use Cases

### Testing with Mocks

Replace production services with test doubles while keeping everything else:

```python
# Production setup
app_container = Container(registry)
app_container.add(DatabaseConnection("postgresql://prod-server"))
app_container.add(EmailService(SmtpConfig("prod-smtp.company.com")))
app_container.add(PaymentProcessor(StripeConfig("pk_live_...")))
app_container.add(Logger(level="INFO"))

# Test setup - override problematic services
test_container = app_container.branch()
test_container.add(DatabaseConnection("sqlite://memory"))  # In-memory test DB
test_container.add(EmailService(MockEmailConfig()))        # Mock email
test_container.add(PaymentProcessor(MockPaymentConfig()))  # Mock payments

# Test inherits logger and other safe services unchanged
# But uses test-specific database, email, and payment services

@inject
def create_user(name: str, email: str, 
                db: Inject[DatabaseConnection],
                email_service: Inject[EmailService],
                payment: Inject[PaymentProcessor]):
    # This function works identically in both containers
    # but uses different implementations
    pass

# Test uses mock services
test_container.call(create_user, "Test User", "test@example.com")

# Production uses real services  
app_container.call(create_user, "Real User", "real@example.com")
```

### Request Scoping

Add request-specific data while sharing application-level services:

```python
# Application-level container
app_container = Container(registry)
app_container.add(DatabasePool(max_connections=20))
app_container.add(CacheService(redis_url="redis://cache-cluster"))
app_container.add(ConfigService())
app_container.add(MetricsCollector())

def handle_request(request):
    # Create request-scoped container
    request_container = app_container.branch()
    
    # Add request-specific data
    request_container.add(CurrentUser(request.user_id))
    request_container.add(RequestContext(request.id, request.headers))
    request_container.add(SessionData(request.session))
    
    # Services that need request context get it automatically
    # while still accessing shared database pool and cache
    return request_container.call(process_request)

@inject
def process_request(user: Inject[CurrentUser],
                   db_pool: Inject[DatabasePool],      # From app container
                   cache: Inject[CacheService],        # From app container
                   context: Inject[RequestContext]):   # From request container
    # Can access both request-specific and application-level dependencies
    pass
```

### Environment Configuration

Share common configuration while overriding environment-specific services:

```python
# Base configuration shared across environments
base_container = Container(registry)
base_container.add(Logger())
base_container.add(MetricsCollector())
base_container.add(ConfigLoader())
base_container.add(SecurityValidator())

# Development environment
dev_container = base_container.branch()
dev_container.add(DatabaseConnection("localhost:5432"))
dev_container.add(RedisCache("localhost:6379"))
dev_container.add(EmailService(LoggingEmailService()))  # Just log emails
dev_container.add(PaymentProcessor(MockPaymentProcessor()))

# Staging environment  
staging_container = base_container.branch()
staging_container.add(DatabaseConnection("staging-db:5432"))
staging_container.add(RedisCache("staging-redis:6379"))
staging_container.add(EmailService(TestEmailService()))  # Send to test accounts
staging_container.add(PaymentProcessor(SandboxPaymentProcessor()))

# Production environment
prod_container = base_container.branch()
prod_container.add(DatabaseConnection("prod-cluster:5432"))
prod_container.add(RedisCache("prod-redis-cluster:6379"))
prod_container.add(EmailService(SmtpEmailService()))
prod_container.add(PaymentProcessor(LivePaymentProcessor()))

# All environments share logger, metrics, config, and security
# but use environment-appropriate databases, caches, and external services
```

### Plugin Isolation

Isolate plugin dependencies to prevent conflicts:

```python
# Main application container
app_container = Container(registry)
app_container.add(CoreDatabase())
app_container.add(UserService())
app_container.add(AuthService())

# Plugin A - e.g., analytics plugin
analytics_container = app_container.branch()
analytics_container.add(AnalyticsDatabase("analytics-db"))
analytics_container.add(EventTracker())
analytics_container.add(ReportGenerator())

# Plugin B - e.g., notification plugin  
notification_container = app_container.branch()
notification_container.add(NotificationQueue("notification-queue"))
notification_container.add(TemplateEngine())
notification_container.add(DeliveryService())

# Plugins can access core services but are isolated from each other
# Analytics plugin cannot access notification queue
# Notification plugin cannot access analytics database
# Both can access core database and user service
```

### Multi-Tenant Applications

Isolate tenant-specific data while sharing core infrastructure:

```python
# Shared infrastructure
base_container = Container(registry)
base_container.add(DatabasePool())
base_container.add(CacheCluster())
base_container.add(FileStorage())
base_container.add(EmailInfrastructure())

def get_tenant_container(tenant_id: str) -> Container:
    tenant_container = base_container.branch()
    
    # Tenant-specific configuration
    tenant_config = load_tenant_config(tenant_id)
    tenant_container.add(TenantConfig(tenant_config))
    tenant_container.add(TenantDatabase(tenant_config.db_name))
    tenant_container.add(TenantTheme(tenant_config.theme))
    tenant_container.add(TenantFeatures(tenant_config.enabled_features))
    
    return tenant_container

# Each tenant gets isolated configuration
tenant_a_container = get_tenant_container("tenant-a")
tenant_b_container = get_tenant_container("tenant-b")

# But shares infrastructure like database pools and file storage
```

## When NOT to Use Branching

### Complete Application Separation
```python
# DON'T: Branch for completely different applications
user_app = base_container.branch()      # ❌ Wrong
admin_app = base_container.branch()     # ❌ Wrong  

# DO: Use separate containers
user_app = Container(user_registry)     # ✅ Correct
admin_app = Container(admin_registry)   # ✅ Correct
```

### Simple Configuration Overrides  
```python
# DON'T: Branch just to change a config value
debug_container = prod_container.branch()           # ❌ Overkill
debug_container.add(Logger(level="DEBUG"))          # ❌ Overkill

# DO: Use qualified dependencies
prod_container.add(Logger, Logger(level="INFO"), qualifier="production")    # ✅ Better
prod_container.add(Logger, Logger(level="DEBUG"), qualifier="debug")        # ✅ Better
```

### One-off Testing
```python
# DON'T: Branch for simple unit tests
def test_user_service():
    test_container = app_container.branch()    # ❌ Unnecessary
    test_container.add(MockDatabase())         # ❌ Unnecessary
    # ...

# DO: Mock at the function level
def test_user_service():
    mock_db = MockDatabase()
    user_service = UserService(mock_db)        # ✅ Simpler
    # ...
```

## Decision Tree

Use this flowchart to decide when to use container branching:

```
Do you need to override some (but not all) dependencies?
├─ YES → Do the new dependencies need to be isolated from other contexts?
│  ├─ YES → Use container.branch() ✅
│  └─ NO → Consider qualified dependencies instead
└─ NO → Do you need completely separate dependency graphs?
   ├─ YES → Use separate Container instances
   └─ NO → Use the existing container
```

## Best Practices

### 1. Name Your Containers Clearly
```python
# Good: Purpose is clear
test_container = app_container.branch()
request_container = app_container.branch()
dev_environment = base_config.branch()

# Bad: Purpose is unclear
container2 = container1.branch()
temp_container = main_container.branch()
```

### 2. Document Override Reasons
```python
test_container = app_container.branch()
# Override database for isolated testing
test_container.add(DatabaseConnection("sqlite://memory"))
# Override email to prevent sending real emails in tests  
test_container.add(EmailService(LoggingEmailService()))
```

### 3. Keep Hierarchies Shallow
```python
# Good: Shallow hierarchy
app → test
app → dev  
app → prod

# Bad: Deep nesting (harder to understand)
app → env → region → tenant → request → user
```

### 4. Clean Up When Done
```python
def handle_request(request):
    request_container = app_container.branch()
    try:
        # ... process request
        return response
    finally:
        # Container will be garbage collected
        # No explicit cleanup needed for branching
        pass
```

## Performance Considerations

### Memory Usage
- Child containers only store their own instances plus a reference to parent
- Shared instances are not duplicated in memory
- Deep hierarchies use more memory for parent references

### Resolution Speed  
- Resolution checks child first, then walks up parent chain
- Deep hierarchies have slightly slower resolution
- Factory caching mitigates repeated resolution costs

### Garbage Collection
- Child containers can be garbage collected independently
- Parent containers stay alive as long as children reference them
- No circular references - children reference parents, not vice versa

## Troubleshooting

### Problem: Child doesn't see parent's instance
```python
# Check: Did you add the instance to parent before branching?
parent.add(SomeService())
child = parent.branch()
service = child.get(SomeService)  # Should work

# Not: 
child = parent.branch()
parent.add(SomeService())  # Added after branching
service = child.get(SomeService)  # Will still work - inheritance is dynamic
```

### Problem: Changes affecting wrong container
```python
# Check: Are you modifying the right container?
child1 = parent.branch()
child2 = parent.branch()

child1.add(SomeService())  # Only affects child1
child2.get(SomeService)    # Will fail - child2 doesn't have it
```

### Problem: Factory called multiple times
```python
# Check: Are you using the same factory function object?
def factory1(): return Service()
def factory2(): return Service()  # Different function!

parent.get(Service, default_factory=factory1)
child.get(Service, default_factory=factory2)  # Will call factory2!

# Use the same factory function for caching:
service_factory = lambda: Service()
parent.get(Service, default_factory=service_factory)
child.get(Service, default_factory=service_factory)  # Reuses cached result
```

This guide should help you use container branching effectively in your applications. For more advanced scenarios, see the API documentation for `Container.branch()` and related methods.