from __future__ import annotations
from typing import Any, Generic, Type, TypeVar
from bevy import Context


T = TypeVar("T")


class LabelAnnotation(Generic[T]):
    def __init__(self, labelled_type: Type[T], label: str):
        self.label = label
        self.type = labelled_type

    def __bevy_build__(self, bevy_context: Context, *args, **kwargs) -> Label[T]:
        inst = bevy_context.construct(self.type, *args, **kwargs)
        label = Label(inst, self.label)
        bevy_context.add(label)
        return label

    def __call__(self, *args, **kwargs) -> LabelAnnotation:
        return self

    def __bevy_inject__(
        self,
        inject_into: Any,
        name: str,
        context: Context,
        *args,
        **kwargs,
    ):
        label = context.get(self, *args, **kwargs)
        setattr(inject_into, name, label.inst)

    def __repr__(self):
        return f"<{type(self).__name__} label={self.label!r} type={self.type!r}>"


class Label(Generic[T]):
    """Labels allow a Bevy context context to have multiple instances of the same type without them conflicting.
    The Label class can be used either as a callable or as an annotation. Calling it will create an instance that wraps
    an object instance and can be added to a context. Using it as an annotation you pass in the type being labelled
    and after a colon the string that is to be used as the label:
    ```py
    @injectable
    class Example:
        dependency: Label[Dependency: "example_dependency"]
    ```
    This will return a LabelAnnotation object that Bevy can use to build and inject an instance of the labelled
    dependency."""

    def __init__(self, labelled_inst: T, label: str):
        self.inst = labelled_inst
        self.label = label

    def __bevy_is_match__(self, obj: Any):
        return (
            isinstance(obj, LabelAnnotation)
            and self.label == obj.label
            and (
                isinstance(self.inst, obj.type)
                or (issubclass(obj.type, type(self.inst)))
            )
        )

    def __class_getitem__(cls, item: slice):
        return LabelAnnotation(item.start, item.stop)

    def __repr__(self):
        return f"<{type(self).__name__} label={self.label!r} instance={self.inst!r}>"
