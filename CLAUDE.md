# Bevy Development Guide

This file contains important information for maintaining and developing the Bevy dependency injection framework.

## Release Procedure

### 1. Update Version Number

Update the version in `pyproject.toml`:
```toml
[tool.poetry]
version = "3.1.1"  # Update this line
```

### 2. Generate Release Notes

Create release notes for the new version:
```bash
python .github/create_release_notes.py 3.1.1
```

This creates `RELEASE_NOTES_3.1.1.md` with a template. Edit this file to include:
- **Features**: New functionality added
- **Improvements**: Enhancements to existing features  
- **Bug Fixes**: Issues resolved
- **Breaking Changes**: Any API changes (if applicable)
- **Migration Guide**: Instructions for upgrading (if needed)

### 3. Create and Push Release Tag

```bash
# Ensure main branch is up to date
git checkout main
git pull origin main

# Commit version and release notes changes
git add pyproject.toml RELEASE_NOTES_3.1.1.md
git commit -m "Prepare release 3.1.1"
git push origin main

# Create and push version tag
git tag v3.1.1
git push origin v3.1.1
```

### 4. Monitor Release Process

1. Watch GitHub Actions tab for the release workflow
2. Verify GitHub release was created successfully
3. Check that PyPI package was published
4. Test installation: `pip install bevy==3.1.1`

## Testing Commands

Run these commands before releasing:

```bash
# Run full test suite
poetry run python -m pytest tests/ -v

# Run type checking
poetry run mypy bevy/

# Run linting (if configured)
poetry run ruff check bevy/
```

## Project Structure

- `bevy/` - Main package code
  - `containers.py` - Core dependency injection container
  - `factories.py` - Factory registration and management
  - `hooks.py` - Hook system for injection lifecycle
  - `injections.py` - Injection decorators and utilities
  - `registries.py` - Type and dependency registries
- `tests/` - Test suite
- `docs/` - Documentation
- `.github/` - GitHub Actions workflows and release automation

## Key Architecture Concepts

### Container Inheritance
- Child containers inherit from parent containers
- `container.get()` and function injection behave identically
- Both check parent containers for existing instances
- Factory functions are used as cache keys

### Injection Flow
1. Check for qualified dependencies first
2. Use default factory if specified (takes precedence over existing instances)
3. Fall back to normal resolution flow
4. Traverse parent containers if needed

### Caching Strategy
- Factory functions (not types) are used as cache keys
- Ensures identical behavior between `container.get()` and `@inject`
- Maintains proper parent-child inheritance and sibling isolation

## Development Workflow

1. Create feature branch from `main`
2. Implement changes with tests
3. Run test suite locally
4. Create pull request to `main`
5. After merge, follow release procedure above

## Troubleshooting

### Tests Failing
- Check for test contamination (global registry state)
- Run individual test files to isolate issues
- Verify imports and dependencies

### Release Issues
- Ensure version in `pyproject.toml` matches tag
- Check GitHub Actions logs for detailed errors
- Verify PyPI trusted publisher is configured correctly

### Container Issues
- Remember that factory functions are cache keys
- Check parent-child relationships in container hierarchy
- Verify qualified vs unqualified dependency resolution