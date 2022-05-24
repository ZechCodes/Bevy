from __future__ import annotations
from functools import wraps
from typing import Callable, ParamSpec, TypeVar, Type
import inspect

from bevy.provider import Provider, NOTSET
from bevy.base_context import BaseContext
import bevy.inject as inj


P = ParamSpec("P")
T = TypeVar("T")


class FunctionProvider(Provider):
    def __init__(
        self,
        func: Callable[P, T],
        context: BaseContext | None = None,
        *,
        use: Callable[P, T] | NOTSET = NOTSET,
    ):
        self._context = context
        self._func = func
        self._use = use
        self._bound_function = None

    def create(self, func: Callable[P, T], *_, **__) -> Callable[P, T]:
        return self.get_instance()

    def get_instance(self) -> Callable[P, T]:
        if self._use:
            return self._use

        if not self._bound_function:
            self._bound_function = self._bind_function()

        return self._bound_function

    def is_matching_type(self, func: Callable[P, T]) -> bool:
        if func is self._func:
            return True

        return self._signatures_exact_type_match(self._func, func)

    def _signatures_exact_type_match(self, func_1, func_2) -> bool:
        sig_1 = inspect.signature(func_1)
        sig_2 = inspect.signature(func_2)

        if sig_1.return_annotation != sig_2.return_annotation:
            return False

        return self._get_signature_types(sig_1) == self._get_signature_types(sig_2)

    def _get_signature_types(self, sig: inspect.Signature) -> list[Type]:
        return [param.annotation for param in sig.parameters.values()]

    def _bind_function(self) -> Callable[P, T]:
        signature = inspect.signature(self._func)
        inject = {
            name: parameter.annotation
            for name, parameter in signature.parameters.items()
            if parameter.default is inj.Inject
        }

        @wraps(self._func)
        def call(*args, **kwargs):
            params = signature.bind_partial(*args, **kwargs)
            params.arguments |= {
                name: self._context.get(annotation)
                for name, annotation in inject.items()
                if name not in params.arguments
            }
            return self._func(*params.args, **params.kwargs)

        return call

    def bind_to(self, context: BaseContext) -> FunctionProvider:
        return type(self)(self._func, context, use=self._use)

    def __eq__(self, other):
        return other.is_matching_provider_type(type(self)) and other.is_matching_type(
            self._func
        )

    def __repr__(self):
        return f"{type(self).__name__}<{self._func!r}, bound={bool(self._context)}, use={self._use}>"
