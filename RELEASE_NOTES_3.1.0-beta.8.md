# Bevy 3.1.0-beta.8

## Highlights
- Reworked dependency-injection flow around a new `InjectableCallable` wrapper so injection metadata and execution live in one place.
- Simplified `Container.call` to delegate to `InjectableCallable`, ensuring the invoking container always drives injection.
- Fixed global-container handling when registries are used via context managers and documented the double-injection edge case with extra decorators.
- Added comprehensive tests covering auto-injection for instance, class, and static methods plus updated documentation to reflect the new behaviour.

## Upgrading
Install or upgrade with:

```bash
pip install --upgrade bevy==3.1.0-beta.8
```

## Contributors
- @zechcodes
