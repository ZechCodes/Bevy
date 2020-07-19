# <img src="https://github.com/ZechCodes/Bevy/raw/master/res/icon.svg" width="128px" align="right" />

# Bevy
Bevy makes using *Dependency Inversion* a breeze so that you can focus on creating amazing code.

## Dependency Inversion
Put simply, *Dependency Inversion* is a design pattern where the objects that your class depends on are instantiated outside of the class. Those dependencies are then injected into your class when it is instantiated.
This promotes loosely coupled code where your class doesn’t require direct knowledge of what classes it depends on or how to create them. Instead your class declares what class interface it expects and an outside framework handles the work of creating the class instances with the correct interface.
## Interfaces
Python doesn’t have an actual interface implementation like many other languages. Class inheritance, however, can be used in a very similar way since sub classes will likely have the same fundamental interface as their base class. 
## Why Do I Care?
*Dependency Inversion* and its reliance on abstract interfaces makes your code easier to maintain:
- Changes can be made without needing to alter implementation details in unrelated code, so long as the interface isn’t modified in a substantial way.
- Tests can provide mock implementations of dependencies without needing to jump through hoops to inject them. They can provide the mock to the context and Bevy will make sure it is used where appropriate.
## How Bevy Works
Bevy allows your class to say what dependencies it has by using undefined class attribute annotations. That’s a bit vague so here is an example:
```py
class MyClass(Bevy):
    my_dependency: MyDependency
```
The class `MyClass`has a dependency on the `MyDependency` interface. It wants this dependency to be made available with the attribute name `my_dependency`. This will allow your class to access an instance of `MyDependency`as `self.my_dependency`, even from `__init__` since the injection happens when `__new__` is called.

It is important to note that Bevy ignores any class attribute that has been assigned to. For example:
```py
my_dependency: MyDependency = MyDependency()
```
This will be ignored by the dependency resolver because it’s been assigned a value.
## Dependency Resolution
Dependency resolution and injection is handled when `__new__` is called. Bevy keeps a repository of all dependencies that have already been created in a context. This repository is used to look for each of the dependency class interfaces when a Bevy class is created. A dependency will be used from the repository only if it is the same class as the interface requested or a sub-class of that interface. If no match is found for an interface, instance will be created without arguments and saved to the repository.

So, in short, all dependencies are guaranteed to be either the same class as the dependency’s interface or a sub class of that interface.
## How To Customize Dependencies
If you need to instantiate a dependency with arguments or provide an alternate implementation of a dependency you can create a custom context.
```py
from bevy import Context
context = Contex().load(MyDependency(foo="bar"))
app = context.create(MyApp, "some instantiation args")
```
It is important to note that `Context.create` does not add the instance returned to the context repository. If that is necessary use `Context.get`, or if you need to pass instantiation arguments use `Context.load` passing the instance returned by `Context.create`.
## Dependency Factories
It is also possible to create a factory for any of your dependencies. Instances generated by a factory will not be added to the context repository since they will not be unique in the context. Creating a factory is as simple as annotating a class attribute with the bevy factory class and telling it what dependency type it should create.
```py
from bevy import Bevy, Factory
class MyApp(Bevy):
    factory: Factory[My_Dependency]
    def get_instance(self, name: str) -> My_Dependency:
        return self.factory(name)
```
## Accessing The Context
You can give a Bevy object access to the context that created it by adding a class attribute annotated with the `Context` type. This will cause the current context instance to inject itself into your class.
```py
from bevy import Bevy, Context
class MyApp(Bevy):
    context: Context
```
## Scoped Contexts
It is possible to branch a context to create a child context which has access to everything in its repository and in the repositories of its parent contexts, while the parents do not have access to the repository of the child. This might be used for a plugin system where you’d want the plugin to have access to the dependencies of the app but you wouldn’t want the plugin to pollute the app’s context.
```py
class MyApp(Bevy):
    context: Context
    def __init__(self, plugins: List[Type[Plugin]]):
        self.plugins = self.load_plugins(plugins)
    def load_plugins(self, plugins: List[Type[Plugin]]) -> List[Plugin]:
        plugin_instances = []
        for plugin in plugins:
            instance = self.context.branch().create(plugin)
            plugin_instances.append(instance)
        return plugin_instances
```
## Driving Motivations
The motivations that drive the decisions about how Bevy is implemented are as follows.
- It should feel like nothing has been changed from normal.
- IDEs should be able to understand what is happening.
- Everything should work independently.
## Future
- Add support for circular dependencies. Likely use descriptors to lazily inject dependencies.
- Add more tests that cover cases beyond the main use cases.
