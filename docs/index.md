# Bevy

Bevy is a refreshingly simple dependency injection framework for Python. It's as simple as using the `bevy.inject` decorator, the `bevy.dependency` descriptor, and type hints to declare dependencies on your functions, methods, and class objects.

## Getting Started

Install bevy using pip:
```bash
pip install bevy
```
Then, you only need to import the core functions from `bevy`:
```python
from bevy import inject, dependency
```

## Usage

### Injecting Function Parameters

Bevy fully understands function parameters and will correctly handle positional only, positional, keyword, and keyword only arguments. It also understands what is being passed into the function and will only inject the dependencies that aren't already being passed.
```python
from bevy import inject, dependency

@inject
def example(arg: Demo = dependency()):
    ...
```

### Injecting Class Attributes

Bevy also understands class attributes and can inject them on class instances. To help keep instantiation, Bevy lazily inject dependencies on demand.
```python
from bevy import dependency

class Example:
    attr: Demo = dependency()
```