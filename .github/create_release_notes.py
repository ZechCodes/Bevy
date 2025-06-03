#!/usr/bin/env python3
"""
Script to create release notes template for a new version.
Usage: python .github/create_release_notes.py <version>
Example: python .github/create_release_notes.py 3.1.0
"""

import sys
import os
from pathlib import Path

def create_release_notes_template(version: str) -> str:
    """Create a release notes template for the given version."""
    
    # Determine if this is a pre-release
    is_prerelease = any(marker in version.lower() for marker in ['alpha', 'beta', 'rc'])
    
    # Format version for pip install
    pip_version = version
    if 'beta' in version.lower():
        pip_version = version.replace('beta', 'b').replace('beta.', 'b')
    elif 'alpha' in version.lower():
        pip_version = version.replace('alpha', 'a').replace('alpha.', 'a')
    elif 'rc' in version.lower():
        pip_version = version.replace('rc', 'rc').replace('rc.', 'rc')
    
    template = f"""# Bevy {version} Release 🚀

## 🌟 Major Features

### [Feature Title]
- **[Feature Description]**: Brief description of the new feature
- **[Technical Detail]**: Implementation details
- **[Benefit]**: What this enables for users

## 🔧 Technical Improvements

### [Improvement Category]
- **[Improvement Title]**: Description of technical improvement
- **[Impact]**: What this improves

### Developer Experience
- **[Enhancement]**: Description of developer experience improvement
- **[Tooling]**: New tools or improved tooling

## 📚 Documentation Updates

- **[Documentation Update]**: Description of documentation changes
- **[Guide Update]**: New or updated guides

## 🧪 Testing & Quality

### Test Coverage
- **[Test Area]**: Description of new tests
- **[Coverage Metric]**: Testing metrics or coverage improvements

## 💡 Usage Examples

### New Feature Example:
```python
# Example of new functionality
from bevy import injectable, Inject
from bevy.injection_types import Options

@injectable
def example_function(service: Inject[ExampleService]):
    return service.do_something()
```

## 🔄 Migration Guide

{"1. **Breaking Change**: Description of any breaking changes and how to migrate" if not is_prerelease else "No breaking changes in this release."}

## ⚠️ Breaking Changes

{"- **[Breaking Change]**: Description of breaking change" if not is_prerelease else "None in this pre-release."}

## 🐛 Bug Fixes

- Fixed [issue description]
- Improved [area] by [description]
- Enhanced [component] to [improvement]

## 🙏 Acknowledgments

Thank you to all contributors who made this release possible!

---

**Full Changelog**: [View on GitHub](https://github.com/ZechCodes/Bevy/compare/v[PREVIOUS_VERSION]...v{version})

**Installation**: `pip install bevy=={pip_version}`

**Feedback**: Please report any issues or feedback on our [GitHub Issues](https://github.com/ZechCodes/Bevy/issues) page.
"""
    
    return template

def main():
    if len(sys.argv) != 2:
        print("Usage: python .github/create_release_notes.py <version>")
        print("Example: python .github/create_release_notes.py 3.1.0")
        sys.exit(1)
    
    version = sys.argv[1].strip()
    
    # Validate version format (basic validation)
    if not version.replace('.', '').replace('-', '').replace('alpha', '').replace('beta', '').replace('rc', '').isalnum():
        print(f"Error: Invalid version format: {version}")
        sys.exit(1)
    
    # Create release notes content
    content = create_release_notes_template(version)
    
    # Write to file
    filename = f"RELEASE_NOTES_{version}.md"
    filepath = Path(__file__).parent.parent / filename
    
    if filepath.exists():
        response = input(f"{filename} already exists. Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("Aborted.")
            sys.exit(0)
    
    with open(filepath, 'w') as f:
        f.write(content)
    
    print(f"✅ Created {filename}")
    print(f"📝 Please edit the file to add specific release details")
    print(f"🏷️  When ready, create a git tag: git tag v{version}")
    print(f"🚀 Push the tag to trigger release: git push origin v{version}")

if __name__ == "__main__":
    main()