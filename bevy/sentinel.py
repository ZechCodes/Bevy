from functools import cache
from typing import Type


@cache
def sentinel(name: str, truthy: bool = False) -> Type:
    class SentinelMCS(type):
        def __bool__(self):
            return truthy

        def __eq__(self, other):
            return False

        def __hash__(self):
            return id(self)

        def __repr__(self):
            return f"<{self.__name__}>"

    return SentinelMCS(
        name,
        (object,),
        {}
    )
