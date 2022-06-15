from functools import wraps
from inspect import signature, Signature
from typing import Callable, ParamSpec, Type, TypeVar

from bevy.inject import Bevy
from bevy.inject.inject_strategies import is_inject
from bevy.providers.base import BaseProvider
from bevy.sentinel import sentinel
from fast_protocol import protocol


T = TypeVar("T")
P = ParamSpec("P")
KeyObject = Callable[P, T]
ValueObject = Callable[P, T]


NOT_FOUND = sentinel("NOT_FOUND")


CallableProtocol = protocol("__call__")


class FunctionProvider(BaseProvider, Bevy, priority="high"):
    def __init__(self, *_, **__):
        super().__init__()
        self._repository = {}

    def add(self, obj: ValueObject, *, use_as: KeyObject | None = None):
        self._repository[use_as or obj] = obj

    def bind_to_context(self, obj: KeyObject, context) -> KeyObject:
        return self._bind_function(obj, context)

    def create(self, obj: KeyObject, *args, add: bool = False, **kwargs) -> ValueObject:
        func = self.bind_to_context(obj, self.bevy)
        if add:
            self.add(func, use_as=obj)

        return func

    def get(
        self, obj: KeyObject, default: ValueObject | T | None = NOT_FOUND
    ) -> ValueObject | T | None:
        for key, value in self._repository.items():
            if self._signatures_exact_type_match(obj, key):
                return value

        if default is NOT_FOUND:
            return obj

        return default

    def has(self, obj: KeyObject) -> bool:
        return self.get(obj, NOT_FOUND) is not NOT_FOUND

    def supports(self, obj: KeyObject) -> bool:
        return not isinstance(obj, type) and isinstance(obj, CallableProtocol)

    def _signatures_exact_type_match(self, func_1, func_2) -> bool:
        sig_1 = signature(func_1)
        sig_2 = signature(func_2)

        if sig_1.return_annotation != sig_2.return_annotation:
            return False

        return self._get_signature_types(sig_1) == self._get_signature_types(sig_2)

    def _get_signature_types(self, sig: Signature) -> list[Type]:
        return [param.annotation for param in sig.parameters.values()]

    def _bind_function(self, func: ValueObject, context) -> ValueObject:
        sig = signature(func)
        inject = {
            name: parameter.annotation
            for name, parameter in sig.parameters.items()
            if is_inject(parameter.default)
        }

        @wraps(func)
        def call(*args, **kwargs):
            params = sig.bind_partial(*args, **kwargs)
            params.arguments |= {
                name: self.bevy.get(annotation)
                for name, annotation in inject.items()
                if name not in params.arguments
            }
            return func(*params.args, **params.kwargs)

        return call


def bevy_method(method):
    @wraps(method)
    def inject(s: Bevy, *args, **kwargs):
        return s.bevy.bind(method)(s, *args, **kwargs)

    return inject
