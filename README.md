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
Python doesn’t have an actual interface implementation like many other languages. Class inheritance, however, can be used in a very similar way since subclasses will likely have the same fundamental interface as their base class. 

## Why Do I Care?
*Dependency Injection* and its reliance on abstract interfaces makes your code easier to maintain:
- Changes can be made without needing to alter implementation details in unrelated code, so long as the interface isn’t modified in a substantial way.
- Tests can provide mock implementations of dependencies without needing to jump through hoops to inject them. They can provide the mock to the context and Bevy will make sure it is used where appropriate.

## How It Works
Bevy is an object oriented *dependency injection* framework. Similar to Pydantic, it relies on Python 3's class
annotations, using them to determine what dependencies a class has.

**Example**
```py
from bevy.injection import AutoInject, detect_dependencies
@detect_dependencies
class Example(AutoInject):
    dependency: Dependency
```
Each dependency when instantiated is added to a context repository for reuse. This allows many classes to share the same
instance of each dependency. This is handy for sharing things like database connections, config files, or authenticated
API sessions.

## Bevy Constructors

To instantiate classes and have Bevy inject their dependencies it is necessary to bind them to a 
`bevy.injection.Context`. This will give a callable that will build instances that are bound to the context.

**Example**
```py
import bevy.injection
context = bevy.injection.Context()
builder = context.bind(Example)
example = builder()  # An instance of Example will be created
```
### Configuring Dependencies

When the `Context` encounters a dependency that is not in its repository it will attempt to create the
dependency. The approach is very naive, it will just call the dependency with no arguments. If it succeeds it will be
added to the repository for later use and injected into the class.

This behavior can be changed by passing an instantiated dependency to `Context.add`.
**Example**
```py
context.add(Dependency("foobar"))
```

### Getting Instances
You can get an instance of a class by using `Context.get` or `Context.get_or_create`. `get_or_create` will naively create an instance of the requested class if it is not found.
**Example**
```python
inst = context.get(Dependency)
```
