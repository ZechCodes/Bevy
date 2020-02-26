![Exo](res/icon.svg)
# Exo
Exo makes using *Dependency Inversion* a breeze so that you can focus on creating amazing code.
## Dependency Inversion
Put simply, *Dependency Inversion* is a design pattern where the objects that your class depends on are instantiated outside of the class. Those dependencies are then injected into your class when it is instantiated.
This promotes loosely coupled code where your class doesn’t require direct knowledge of what classes it depends on or how to create them. Instead your class declares what class interface it expects and an outside framework handles the work of creating the class instances with the correct interface.
## Interfaces
Python doesn’t have an actual interface implementation like many other languages. Class inheritance, however, can be used in a very similar way since sub classes will likely have the same fundamental interface as their base class. 
## Why Do I Care?
*Dependency Inversion* and its reliance on abstract interfaces makes your code easier to maintain:
- Changes can be made without needing to alter implementation details in unrelated code, so long as the interface isn’t modified in a substantial way.
- Tests can provide mock implementations of dependencies without needing to jump through hoops to inject them. They can provide the mock to the builder and Exo will make sure it is used where appropriate.
## How Exo Works
Exo allows your class to say what dependencies it has by using undefined class attribute annotations. Yeah… That’s not clear at all… Ok, here’s an example:
```py
class MyClass(Exo):
    my_dependency: MyDependency
```
Now to explain. `MyClass` has a dependency on the `MyDependency` interface. It wants this dependency to be made available with the attribute name `my_dependency`. This will allow your class to access an instance of `MyDependency` as `self.my_dependency`, it’ll even be available when `__init__` is called!

It is important to note that this cannot be assigned a value. For example:
```py
my_dependency: MyDependency = MyDependency()
```
This will be ignored by the dependency resolver because it’s been assigned a value.
## Dependency Resolution
Dependency resolution and injection is handled right after `__new__` is called. Exo has a repository of all dependencies that have already been created. This repository is used anytime a class is instantiated to look for each of the dependency class interfaces. A dependency will be used from the repository only if it is the same class as the interface requested or a sub class of that interface. If no match is found for an interface, the class interface will be instantiated without arguments.

So, in short, all dependencies are guaranteed to be either the same class as the dependency’s interface or a sub class of that interface.
## How To Customize Dependencies
What if you need to instantiate a dependency with arguments or provide an alternate implementation of a dependency? This can be accomplished by using your class’ builder. The builder can be accessed by calling the `declare` class method, which takes an arbitrary number of object instances as its arguments. These instances will then be saved in the repository and will be used as dependencies for any matching interface. `declare` returns an `ExoBuilder` instance so you will need to call its `build` method.

Example *(continuing the code from above)*:
```py
app = MyClass \
    .declare(MyDependency(foo=“bar”)) \
    .build()
```
## Driving Motivations
The motivations that drive the decisions about how Exo is implemented are as follows.
- It should feel like nothing has been changed from normal.
- IDEs should be able to understand what is happening.
- Everything should work independently.
## Future
Currently there isn’t much planned. The goal was to make this fairly straightforward and not to overload it with a million features.
- Add support for circular dependencies. Likely use descriptors to lazily inject dependencies.
