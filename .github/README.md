# GitHub Actions Workflows

This directory contains the GitHub Actions workflows for the Bevy project.

## Workflows

### 🚀 Release Workflow (`release.yaml`)

Automatically creates GitHub releases and publishes to PyPI when a version tag is pushed.

**Triggers**: Push of tags matching `v*` (e.g., `v3.1.0`, `v3.1.0-beta.1`)

**Features**:
- ✅ Runs full test suite before release
- 📝 Uses release notes file if available (`RELEASE_NOTES_<version>.md`)
- 📦 Builds Python packages (wheel + sdist)
- 🏷️ Creates GitHub release with artifacts
- 🐍 Publishes to PyPI using trusted publisher (no token needed!)
- 🔍 Auto-detects pre-releases (beta, alpha, rc)
- 🛡️ Uses environment protection for PyPI publishing

**Usage**:
```bash
# Create release notes (optional but recommended)
python .github/create_release_notes.py 3.1.1

# Edit the generated RELEASE_NOTES_3.1.1.md file with details

# Create and push tag
git tag v3.1.1
git push origin v3.1.1
```

### 🧪 Tests Workflow (`tests.yaml`)

Runs comprehensive tests on multiple platforms and Python versions.

**Triggers**: 
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop` branches

**Features**:
- 🔄 Tests on Ubuntu, Windows, and macOS
- 🐍 Tests Python 3.10, 3.11, and 3.12
- 📊 Generates coverage reports
- 🔍 Runs linting and type checking
- ⚡ Uses caching for faster runs

## Setup

### PyPI Publishing Setup

The release workflow uses PyPI's trusted publisher feature for secure publishing:

1. **Trusted Publisher** (Recommended): No secrets needed!
   - PyPI automatically trusts GitHub Actions from this repository
   - Publishing happens securely using OIDC tokens
   - Already configured in the `release.yaml` workflow

2. **API Token** (Alternative): Manual token configuration
   - Go to [PyPI Account Settings](https://pypi.org/manage/account/token/)
   - Create a new API token with scope for this project
   - Add as repository secret named `PYPI_TOKEN`

### Repository Settings

Ensure the following repository settings:

1. **Actions permissions**: Allow GitHub Actions to create releases
   - Go to Settings > Actions > General
   - Set "Workflow permissions" to "Read and write permissions"
   - Check "Allow GitHub Actions to create and approve pull requests"

## Release Process

### 1. Prepare Release

```bash
# Create release notes template
python .github/create_release_notes.py 3.1.1

# Edit RELEASE_NOTES_3.1.1.md with actual changes
```

### 2. Create Release

```bash
# Ensure main branch is up to date
git checkout main
git pull origin main

# Create and push tag
git tag v3.1.1
git push origin v3.1.1
```

### 3. Monitor Release

1. Watch the Actions tab for the release workflow
2. Verify the GitHub release was created successfully
3. Check PyPI for the new package version (if publishing enabled)

## File Naming Convention

Release notes files follow this pattern:
- `RELEASE_NOTES_<version>.md`
- Examples: `RELEASE_NOTES_3.1.0.md`, `RELEASE_NOTES_3.1.0-beta.1.md`

The workflow will automatically find and use the correct release notes file based on the tag version.

## Troubleshooting

### Release not created
- Check that the tag follows the `v*` pattern (e.g., `v3.1.0`)
- Verify repository permissions allow Actions to create releases
- Check the Actions logs for error details

### PyPI publishing failed
- Verify the trusted publisher is configured correctly on PyPI
- Check that the version doesn't already exist on PyPI
- Ensure the repository has the correct permissions (id-token: write)
- If using manual token: verify `PYPI_TOKEN` secret is configured

### Tests failing
- Review the test output in the Actions logs
- Ensure all dependencies are properly specified in `pyproject.toml`
- Check for platform-specific issues if only some OS combinations fail