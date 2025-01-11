# Bevy
Bevy makes using *Dependency Injection* in *Python* a breeze so that you can focus on creating amazing code.

## Installation
```shell script
pip install bevy>3.0.0
```

## Dependency Injection
Put simply, *Dependency Injection* is a design pattern where the objects that your code depends on are instantiated by the caller. Those dependencies are then injected into your code when it is run.
This promotes loosely coupled code where your code doesn't require direct knowledge of what objects it depends on or how to create them. Instead, your code declares what interface it expects and an outside framework handles the work of creating objects with the correct interface.

## Interfaces
Python doesn't have an actual interface implementation like many other languages. Class inheritance, however, can be used in a very similar way since subclasses will likely have the same fundamental interface as their base class. 

## Why Do I Care?
*Dependency Injection* and its reliance on abstract interfaces makes your code easier to maintain:
- Changes can be made without needing to alter implementation details in unrelated code, so long as the interface isn’t modified in a substantial way.
- Tests can provide mock implementations of dependencies without needing to rely on patching or duck typing. They can provide the mock to Bevy which can then ensure it is used when necessary.

## How It Works
Bevy makes use of Python's contextvars to store a registry object global to the context. You can then use `bevy.inject` and `bevy.dependency` to inject dependencies into functions and classes. 

The `dependency` function returns a descriptor that can detect the type hints that have been set on a class attribute. It can then create and return a dependency that matches the type hints.

The `inject` decorator allows you to use the `dependecy` function to inject dependencies into functions. Each parameter that needs to be injected should have its default value set to `dependency()` and then the `inject` decorator will intelligently handle injecting those dependencies into the function arguments based on the parameter type hints. This injection is compatible with positional only, positional, keyword, and keyword only arguments.

**Example**
```py
from bevy import inject, dependency

class Thing:
    ...

class Example:
    foo: Thing = dependency()

@inject
def example(foo: Thing = dependency()):
    ...
```
Each dependency once created is stored in the context global container to be reused by other functions and classes that depend on them. This sharing is very useful for database connections, config files, authenticated API sessions, etc.

**Setting Values In the Container**

It is possible to provide a value to the context's global repository that will be used as a dependency.You can get the current repository using the `bevy.get_repository` function, you can then use that repository's `set` method to assign an instance to a given key.
```python
from bevy import get_repository

get_repository().set(Thing, Thing("foobar"))
```
This would cause anything that has a dependency for `Thing` to have the instance `Thing("foobar")` injected.

The `set` method will return an empty `bevy.options.Value` object if it succeeds in setting the value into the cache or will return a `bevy.options.Null` object if it fails.

**Getting Values From the Repository**

It is possible to get values directly from the repository using its `get` method.
```python
from bevy import get_repository

thing = get_repository().get(Thing)
```
If an instance of `Thing` is not found in the cache it will create an instance, save it in the cache for future use, and then return it.

It is possible to get a value from the cache without creating an instance if it's not found using the `find` method. This method returns an `Option` type that can either be your value wrapped in a `Value` type or a `Null` type if the value was not found. You can use the `value_or` method to get your value or a default if it doesn't exist.
```python
thing = get_repository().find(Thing).value_or(None)
```
It is also possible to use match/case to unwrap the value with more flexibility.
```python
from bevy.options import Value, Null

match get_repository().find(Thing):
    case Value(value):
        thing = value
    case Null():
        raise Exception("Could not find an instance of Thing")
```

**Dependency Providers**

To make Bevy as flexible as possible, it has dependency providers. These are classes that can be registered with the repository to cache value instances, look up cached instances using a key type, and create new instances for a key type.

The default repository type has two dependency providers: an annotated provider and a type provider.
- The **Type Provider** handles key types that are class types. So when a dependency annotation is `Thing`, for example, the type provider will handle looking through its cache for an instance of `Thing` and creating an instance if it is not found.
- The **Annotated Provider** handles key types that are instances of `typing.Annotated`. It works very similarly to the type provider except it allows you to provide an annotation. This is helpful if you have multiple instances of the same type that need to exist together. You could have `Annotated[Thing, "testA"]` and `Annotated[Thing, "testB"]`, both of them would be able to point to distinct instances of `Thing` in the same repository cache.

It is possible to add new providers to the repository using it's `add_providers` method which takes any number of provider types.

It is also possible to subclass `bevy.Repository`, provide a custom `factory` class method that returns an instance of `Repository` with whatever default providers you want set. Just call `Repository.set_repository` with an instance of the new repository type.
