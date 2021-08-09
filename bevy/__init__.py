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

## Bevy Contexts

To instantiate classes and have Bevy inject their dependencies it is necessary to use a
[`bevy.Context`](#Context). The context takes a [`bevy.Injectable`](#Injectable) and any args necessary to
instantiate it. Calling [`Context.build`](#Context.build) on the context will then create an instance of the
`Injectable` with all dependencies injected.

**Example**
```py
context = bevy.Context(Example)
example = context.build()
```
### Configuring Dependencies

When the `Context` encounters a dependency that is not in the context repository it will attempt to create the
dependency. The approach is very naive, it will just call the dependency with no arguments. If it succeeds it will be
added to the repository for later use and injected into the class.

This behavior can be changed by passing an instantiated dependency to [`Context.add`](#Context.add).
**Example**
```py
context.add(Dependency("foobar"))
```
When adding an `Injectable` it is necessary to use [`Context.branch`](#Context.branch) as it will inherit all
dependencies that are added to the context. Any dependencies added to the branch will not be back propagated to the
context, allowing for dependency isolation. Because branches inherit but do not propagate, their dependency
resolution is deferred until `Context.build` is called, when it is assumed all dependencies with customized
instantiations have been added.

Because `Injectables` require a special lifecycle `Context.branch` will accept any instantiation args that should be
passed to the class when it is constructed.
**Example**
```py
branch = context.branch(Dependency)
```
"""
from bevy.context import Context
from bevy.injectable import injectable, is_injectable


__all__ = ("Context", "injectable", "is_injectable")
