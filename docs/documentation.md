# Bevy Documentation
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

It is possible to pass in overrides to the Bevy context which will be used in place of the requested type. This is great for providing instantiated instances of classes (config models, database connections, etc.) or for test mocks.
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
