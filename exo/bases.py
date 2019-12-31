"""\
Base classes for all Exo classes and exceptions.

Any Exo extension package should make a sub class of the ExoBaseException and
use that for any errors they need to raise. This can be done neatly by calling
the ExoBaseException's 'create' method with the name of the new exception, the
message that should be shown for that exception, and the docs that should be
used. This will return an exception class that is setup and ready to be used.
"""

from __future__ import annotations
from abc import ABCMeta, ABC
from typing import Type


class ExoBaseMeta(ABCMeta):
    """\
    This is the base class for all Exo meta classes.
    """

    ...


class ExoBase(ABC, metaclass=ExoBaseMeta):
    """\
    This is the base class for all Exo classes.
    """

    ...


class ExoBaseException(Exception):
    """\
    This is the base for all Exo exception classes. Any Exo extension packages
    should extend this class with their own package specific base exception.
    """

    message = ""

    def __init__(self, *args, **kwargs):
        """ Build a more advanced message. """
        message = [self.message]
        if args or kwargs:
            message.append("\n  Additional Details:")
            message += map(lambda arg: f"\n  * {arg}", args)
            message += map(lambda item: f"\n  * {item[0]}: {item[1]}", kwargs.items())
        super().__init__("".join(message))

    @classmethod
    def create(cls, /, name: str, message: str, doc: str = "") -> Type:
        """\
        Creates an exception that is a subclass of the ExoBaseException with
        the message and docs values loaded.
        """

        return type(name, (cls,), {"__doc__": doc, "message": message})


ExoInternalException = ExoBaseException.create(
    "ExoInternalException",
    "There was an exception internal to the Exo framework",
    """\
    This is the base class for all Exo internal exceptions. This should not be
    used by any Exo extension packages.
    """
)
