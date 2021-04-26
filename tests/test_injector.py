from pytest import raises
from bevy.injectable import Injectable


def test_injector():
    class Dep:
        def __init__(self, name, instance):
            self.name = name
            self.instance = instance

        @classmethod
        def __bevy_inject__(cls, instance, name):
            return cls(name + "INJECTED", instance)

    class Test(Injectable):
        injected: Dep

        def __init__(self, name):
            self.name = name

    a = Test("Test A")
    b = Test("Test B")

    assert a.injected.name == f"{a.name}INJECTED"
    assert b.injected.name == f"{b.name}INJECTED"
    assert a.injected.instance is a
    assert b.injected.instance is b


def test_almost_injector():
    class Dep:
        def __bevy_inject__(cls, instance, name):
            return

    with raises(TypeError):

        class Test(Injectable):
            injected: Dep
