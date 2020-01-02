from exo.repository import Repository


_extension_repository = Repository()


def get_extensions():
    """ Gets all extensions that have been registered. """
    return _extension_repository.registry


def register(extension_class):
    """ Decorator for registering a class as an extension. """
    _extension_repository.register(extension_class)
    return extension_class


class Extension:
    """ Base class for extensions. """
    ...


__all__ = [Extension, get_extensions, register]
