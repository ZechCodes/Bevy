# Bevy Documentation
Bevy is a simple object oriented dependency injection framework for Python. It works by using class attribute annotations to identify what dependencies a class needs and injects them at instantiation from a shared dependency repository.
## Table of Contents
1. [Usage](#1-usage)
2. [Documentation](#2-documentation)
	1. [Injectable](#2i-injectable)
	2. [Context](#2ii-context)
	3. [Factory](#2iii-factory)
## 1. Usage
Any class that needs dependency injection should inherit from `bevy.Injectable`. Injectables can then be instantiated like normal and Bevy will handle creating a context, instantiating the dependencies, and injecting those dependencies into the new instance.
```py
import bevy

class Example(bevy.Injectable):
    dependency: MyDependency

example = Example()
```
The dependencies will be instantiated without arguments, to get around this it is possible to create a `Context`. An instance can then be added directly to the context and the context can then be used to create instances of injectables with their dependencies.
```py
import bevy

class Example(bevy.Injectable):
    dependency: MyDependency

context = bevy.Context()
context.add(MyDependency("foo", "bar"))
example = context.create(Example)
```
**Dependencies will only be drawn from attribute annotations that have no assigned value**

```py
class Example(bevy.Injector):
    dependency: MyDependency
    not_a_dependency: MyThing = MyThing()
```
Bevy will inject `dependency` but will ignore `not_a_dependency` as it has already been assigned a value.
## 2. Documentation
### 2.i Injectable
#### `class bevy.Injectable`
This is the base class for any class that relies on Bevy to inject dependencies. It provides no methods or attributes, it however does use the `InjectableMeta` metaclass which is necessary for allowing the creation of a context at instantiation. 

#### `type bevy.injectable.InjectableMeta`
*Inherits from* `abc.ABCMeta`
This overrides the class dunder call method to add functionality. When an injectable class  is called the metaclass calls the class`s dunder new method, it then creates a new context, instantiates all of the class’s dependencies, injects them into the instance returned by dunder new, and finally calls the class’s dunder init.  
### 2.ii Context
#### `class bevy.Context`
The context class manages dependency injection and tracks all instantiated dependencies in a shared repository. Anytime an injectable is created it has its dependencies fulfilled from the context’s repository of existing dependencies. If a dependency is not found in the repository the context will attempt to instantiate it without any arguments, that instance will then be added to the repository for future 

#### `method bevy.Context.add(instance)`
Takes an instance and adds it to the context’s repository. If the repository contains an instance that is a superclass or subclass or the same type as the instance being added an exception will be raised.
*Raises* `bevy.context.ConflictingTypeAddedToRepository`
*Returns* `Context` (the instance of `Context` that `add` was called on)

#### `method bevy.Context.branch()`
Creates a new context that inherits from the current context’s repository. This allows the new context to rely on existing dependencies while allowing it to add new dependencies to its own repository without influencing the parent context dependency repository. This is useful in a context of plugins which may want to inherit dependencies but that may have their own that shouldn’t be shared.
*Returns* `Context`

#### `method bevy.Context.create(object_type, *args, **kwargs)`
Creates an instance of a class using the provided args. If `object_type` is a subclass of `bevy.Injectable` the dependencies will be resolved and injected.
*Returns* Instance of `object_type`

#### `method bevy.Context.get(object_type, *, default, propagate=True)`
Gets any instance in the repository that is of the requested type or a subclass of that type. If not found the parent contexts will be checked, if a match is still not found `default` will be returned if set, otherwise an instance will be created and stored in the repository. Parent contexts can be ignored in the lookup by setting `propagate` to `False`.
*Returns* Instance of `object_type` or `default` if set

#### `method bevy.Context.has(object_type, *, propagate=False)`
Checks if any instance in the repository matches the requested type or is a subclass of that type. If not found in the repository it will check the parent contexts unless `propagate` is set to `False`.
*Returns* `bool`

#### `method bevy.Context.find_conflicting_type(search_for_type)`
Checks if any instance in the repository matches the search type, is a subclass of that type, or is a superclass of that type. This will not propagate to parent contexts.
*Returns* `bool`
### 2.iii Factory
#### `class bevy.Factory`
`Factory` is an annotation that takes a type. Bevy will then create a factory function which creates instances of that type which have their dependencies injected at instantiation.

```py
class Example(bevy.Injector):
    create_instance: bevy.Factory[MyClass]
    ...

    def get_instance(arg) -> MyClass:
        return self.create_instance(arg)
```
It is possible to customize the factory behavior by subclassing it and modifying it’s dunder call method. Dunder call should return an instance of `build_type` that has been created by the factory’s context.
**Properties**
`build_type` The class passed to the factory annotation
`context` The context that created the factory
