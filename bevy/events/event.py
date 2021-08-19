from typing import Any


class Event:
    def __init__(self, name: str, *args, **kwargs):
        self._name = name
        self._payload_args = args
        self._payload_kwargs = kwargs

    @property
    def name(self) -> str:
        return self._name

    @property
    def payload_args(self) -> tuple[Any]:
        return self._payload_args

    @property
    def payload_kwargs(self) -> dict[str, Any]:
        return self._payload_kwargs.copy()
