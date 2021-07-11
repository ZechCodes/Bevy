"""Bevy is an object oriented *dependency injection* framework. Similar to Pydantic, it relies on Python 3's class
annotations, using them to determine what dependencies a class has.

**Example**
```py
@bevy.injectable
class Example:
    dependency: Dependency
```
Each dependency when instantiated is added to a context repository for reuse. This allows many classes to share the same
instance of each dependency. This is handy for sharing things like database connections, config files, or authenticated
API sessions.

## Bevy Constructors

To instantiate classes and have Bevy inject their dependencies it is necessary to use a
[`bevy.Constructor`](#Constructor). The constructor takes a [`bevy.Injectable`](#Injectable) and any args necessary to
instantiate it. Calling [`Constructor.build`](#Constructor.build) on the constructor will then create an instance of the
`Injectable` with all dependencies injected.

**Example**
```py
constructor = bevy.Constructor(Example)
example = constructor.build()
```
### Configuring Dependencies

When the `Constructor` encounters a dependency that is not in the context repository it will attempt to create the
dependency. The approach is very naive, it will just call the dependency with no arguments. If it succeeds it will be
added to the repository for later use and injected into the class.

This behavior can be changed by passing an instantiated dependency to [`Constructor.add`](#Constructor.add).
**Example**
```py
constructor.add(Dependency("foobar"))
```
When adding an `Injectable` it is necessary to use [`Constructor.branch`](#Constructor.branch) as it will inherit all
dependencies that are added to the constructor. Any dependencies added to the branch will not be back propagated to the
constructor, allowing for dependency isolation. Because branches inherit but do not propagate, their dependency
resolution is deferred until `Constructor.build` is called, when it is assumed all dependencies with customized
instantiations have been added.

Because `Injectables` require a special lifecycle `Constructor.branch` will accept any instantiation args that should be
passed to the class when it is constructed.
**Example**
```py
branch = constructor.branch(Dependency)
```
"""
from bevy.constructor import Constructor
from bevy.injectable import injectable, is_injectable


__all__ = ("Constructor", "injectable", "is_injectable")
