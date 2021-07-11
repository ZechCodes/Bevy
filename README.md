# Bevy
Bevy makes using *Dependency Injection* a breeze so that you can focus on creating amazing code.

## Installation
```shell script
pip install bevy
```

**[Documentation](docs/documentation.md)**

## Dependency Injection
Put simply, *Dependency Injection* is a design pattern where the objects that your class depends on are instantiated outside of the class. Those dependencies are then injected into your class when it is instantiated.
This promotes loosely coupled code where your class doesn’t require direct knowledge of what classes it depends on or how to create them. Instead your class declares what class interface it expects and an outside framework handles the work of creating the class instances with the correct interface.

## Interfaces
Python doesn’t have an actual interface implementation like many other languages. Class inheritance, however, can be used in a very similar way since sub classes will likely have the same fundamental interface as their base class. 

## Why Do I Care?
*Dependency Injection* and its reliance on abstract interfaces makes your code easier to maintain:
- Changes can be made without needing to alter implementation details in unrelated code, so long as the interface isn’t modified in a substantial way.
- Tests can provide mock implementations of dependencies without needing to jump through hoops to inject them. They can provide the mock to the context and Bevy will make sure it is used where appropriate.

## How It Works
Bevy is an object oriented *dependency injection* framework. Similar to Pydantic, it relies on Python 3's class
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
resolution defers until `Constructor.build` is called, when it is assumed all dependencies with customized
instantiations have been added.

Because `Injectables` require a special lifecycle `Constructor.branch` will accept any instantiation args that should be
passed to the class when it is constructed.
**Example**
```py
branch = constructor.branch(Dependency)
```
