"""\
Base classes for all Exo classes.
"""

from __future__ import annotations
from abc import ABCMeta, ABC


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
