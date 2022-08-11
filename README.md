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
Bevy replies on Python's classes to keep track of dependencies, it however does not require any serious understanding of OOP. Injections rely on Python's type annotations, much like Pydantic. Any class that inherits from the `Bevy` class will be scanned for any attributes that have been assigned the `Inject` object, they will become a descriptor that will handle injecting the appropriate instance to match the annotation of the attribute.

Similarly class methods can use the `bevy_method` decorator, which will look at the method's signature looking for any parameters that have been assigned the `Inject` object. When the method is called it will use the Bevy context attached to the class to inject the appropriate dependencies into the function. If a value is passed to an inject parameter, Bevy will ignore that parameter and not override the passed parameter.  

**Example**
```py
from bevy import Bevy, Inject

class Example(Bevy):
    dependency: Dependency = Inject
```
Each dependency when instantiated is added to a context repository for reuse. This allows many classes to share the same
instance of each dependency. This is handy for sharing things like database connections, config files, or authenticated
API sessions.

### Usage
To use Bevy you can either create an instance of your `Bevy` subclass or you can create a Bevy context and use that to create instances of your classes.
```python
from bevy import Bevy, Inject, Context

class Example(Bevy):
    dependency: Dependency = Inject

context = Context()
example = context.get(Example)
```

**Bevy Methods**
Method parameter injection works quite simply. Just use the decorator and use the `Inject` object to indicate which parameters should be injected when the method is called.
```python
from bevy import Bevy, Inject, Context
from bevy.providers.function_provider import bevy_method

class Example(Bevy):
    @bevy_method
    def demo_method(self, dependency: Dependency = Inject):
        ...

context = Context()
example = context.get(Example)
example.demo_method()
```

**Creating Overrides**
It is possible to pass in overrides to the Bevy context which will be used in place of the requested type.
```python
from bevy import Bevy, Inject, Context

class Example(Bevy):
    dependency: Dependency = Inject

context = Context()
context.add(some_instance, use_as=Dependency)
example = context.get(Example)
```

**Providers**
Bevy has the concept of dependency providers. When a dependency is requested from the Bevy context, the context goes through all registered providers looking for one that can handle the requested type. It then requests that the provider get an instance of the requested type. This is a powerful feature that can be used to dynamically create instances that have a more advanced initialization. I've used this for creating SQLAlchemy database connections and injecting db sessions. I've also used it to inject config models that pull in their values only as needed from a global config object. Bevy's dependency repository then acts as a cache for those objects. 

At this time though, the provider API is actively being refined, so will likely be changed in future versions.

## Future
- Get the providers API nailed down to maximize flexibility and simplicity.
- Support for context managers. Initially I want to have them work with Bevy methods, essentially wrapping the function call in a `with` block. Eventually I'd like to support them at the instance and application levels. This would allow for dependencies that need to be cleaned up when an instance or the context itself is destroyed.
- Auto-detect methods that have used the `Inject` object. 