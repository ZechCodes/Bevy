# Configuration and Module System

## Overview
A comprehensive system for organizing dependencies, managing configuration, and structuring large applications.

## Current Gap
- No configuration binding from files/environment
- No module system for organizing dependencies  
- No auto-discovery of providers/factories
- No profile-based configurations
- No environment-specific dependency registration

## Why This Matters
- Large applications need organized dependency registration
- Environment-specific configurations (dev/test/prod)
- Configuration management and injection
- Reduced boilerplate for dependency setup
- Better separation of concerns

## Implementation Options

### Option 1: Configuration-First Approach
- Configuration files drive dependency registration
- YAML/JSON/TOML configuration with dependency definitions
- Pros: Declarative, easy to modify without code changes
- Cons: Less type safety, potential for runtime errors

### Option 2: Code-First Module System
- Python modules/classes define dependency configurations
- Programmatic registration with type safety
- Pros: Type safe, IDE support, refactorable
- Cons: Requires code changes for configuration

### Option 3: Hybrid Approach
- Modules for complex logic, configuration for simple bindings
- Best of both approaches
- Pros: Flexible, covers all use cases
- Cons: More complex system

## Suggested Implementation Checklist

### Phase 1: Basic Configuration Support
- [ ] Add `ConfigurationContainer` for loading from files
- [ ] Support YAML, JSON, TOML configuration formats
- [ ] Implement environment variable substitution
- [ ] Add configuration validation and error reporting

### Phase 2: Module System
- [ ] Create `Module` base class for dependency organization
- [ ] Implement module registration and loading
- [ ] Add module dependency management (ordering)
- [ ] Support conditional module loading

### Phase 3: Auto-Discovery
- [ ] Implement package scanning for `@inject` decorated classes
- [ ] Add factory auto-discovery by naming conventions
- [ ] Support plugin-style module discovery
- [ ] Add registration validation and conflict detection

### Phase 4: Environment and Profiles
- [ ] Add profile-based configuration (dev/test/prod)
- [ ] Implement environment-specific registrations
- [ ] Support configuration inheritance and overrides
- [ ] Add runtime profile switching

### Phase 5: Advanced Features
- [ ] Configuration hot-reloading
- [ ] Multi-tenant configuration support
- [ ] Configuration templating and generation
- [ ] Integration with external configuration services

## API Design Examples

### Configuration File (YAML):
```yaml
profiles:
  development:
    database:
      url: "sqlite:///dev.db"
      pool_size: 5
    cache:
      type: "memory"
  
  production:
    database:
      url: "${DATABASE_URL}"
      pool_size: 20
    cache:
      type: "redis"
      url: "${REDIS_URL}"

dependencies:
  - type: "myapp.DatabaseService"
    factory: "create_database"
    scope: "singleton"
    config: "{profile}.database"
  
  - type: "myapp.CacheService" 
    factory: "create_cache"
    scope: "singleton"
    config: "{profile}.cache"
```

### Module System:
```python
class DatabaseModule(Module):
    def configure(self, container: Container):
        if self.profile == "development":
            container.register(Database, factory=create_sqlite_db)
        else:
            container.register(Database, factory=create_postgres_db)
            
        container.register(UserRepository)
        container.register(OrderRepository)

class CacheModule(Module):
    depends_on = [DatabaseModule]
    
    def configure(self, container: Container):
        cache_config = self.config.get("cache", {})
        if cache_config.get("type") == "redis":
            container.register(Cache, factory=create_redis_cache)
        else:
            container.register(Cache, factory=create_memory_cache)

# Application setup
app_container = Container()
app_container.load_modules([
    DatabaseModule(profile="production"),
    CacheModule(profile="production")
])
```

### Auto-Discovery:
```python
# Auto-discover all @inject decorated classes in package
container.scan_package("myapp.services")

# Auto-discover by naming convention
container.scan_factories("myapp.factories", pattern="create_*")

# Plugin-style discovery
container.discover_plugins("myapp.plugins")
```

### Environment Configuration:
```python
# Environment-based container setup
container = Container.from_environment(
    config_file="config.yaml",
    profile=os.getenv("APP_PROFILE", "development")
)

# Runtime profile switching
container.switch_profile("testing")
```

## Configuration Features

### Environment Variable Support:
```yaml
database:
  url: "${DATABASE_URL:sqlite:///default.db}"  # Default value
  password: "${DATABASE_PASSWORD}"  # Required variable
  debug: "${DEBUG:false|bool}"  # Type conversion
```

### Configuration Validation:
```python
from bevy.config import ConfigSchema

class DatabaseConfig(ConfigSchema):
    url: str
    pool_size: int = 10
    timeout: float = 30.0

# Automatic validation during container setup
container.validate_config()
```

### Conditional Registration:
```python
class ProductionModule(Module):
    @conditional(lambda env: env.profile == "production")
    def configure_monitoring(self, container):
        container.register(MetricsService)
        container.register(HealthCheckService)
```

## Module Organization Examples

### Large Application Structure:
```
myapp/
├── modules/
│   ├── __init__.py
│   ├── database.py      # DatabaseModule
│   ├── cache.py         # CacheModule  
│   ├── auth.py          # AuthModule
│   └── web.py           # WebModule
├── config/
│   ├── development.yaml
│   ├── testing.yaml
│   └── production.yaml
└── main.py
```

### Module Dependencies:
```python
class AuthModule(Module):
    depends_on = [DatabaseModule, CacheModule]
    
class WebModule(Module):
    depends_on = [AuthModule, DatabaseModule]

# Automatic dependency ordering
container.load_modules_with_dependencies([
    WebModule(), AuthModule(), DatabaseModule(), CacheModule()
])
```

## Testing Integration

### Test-Specific Configuration:
```python
class TestModule(Module):
    def configure(self, container):
        # Override with test implementations
        container.register(Database, factory=create_test_database)
        container.register(EmailService, factory=create_mock_email)

@pytest.fixture
def test_container():
    container = Container()
    container.load_module(TestModule())
    return container
```

## Framework Integration

### FastAPI Integration:
```python
from bevy.integrations.fastapi import setup_bevy

app = FastAPI()
setup_bevy(app, config_file="config.yaml", profile="production")

@app.get("/users")
async def get_users(user_service: UserService = BevyDepends()):
    return await user_service.get_all()
```

## Performance Considerations

### Lazy Loading:
- Load modules only when needed
- Lazy configuration parsing
- On-demand dependency registration

### Caching:
- Cache parsed configurations
- Module registration caching
- Configuration validation caching

## Migration Strategy
- Existing containers continue to work unchanged  
- Gradual adoption of modules and configuration
- Migration tools for converting manual registration

## Priority: Medium-High
Important for large applications and production deployments.

## Estimated Effort: High
Comprehensive feature requiring significant design and implementation.