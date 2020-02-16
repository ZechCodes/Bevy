from exo.exo import Exo, GenericExo
from typing import Awaitable, Iterator, Protocol, Sequence, Type, Union
import asyncio


__all__ = ["ExoApp"]


class Extension(Protocol):
    async def run(self, *args, **kwargs):
        ...


class ExoAppExtensions(Exo):
    def __init__(self):
        self._extensions = []

    def __iter__(self) -> Iterator[Union[Extension, GenericExo]]:
        return iter(self._extensions)

    def add_extension(self, extension: Type[GenericExo]) -> GenericExo:
        """ Adds an extension to the app. """
        ext = self.__repository__.get(extension)
        self._extensions.append(ext)
        return ext

    def load_extensions(self, extensions: Sequence[Type[GenericExo]]):
        """ Loads a collection of extensions into the app from a sequence. """
        for extension in extensions:
            self.add_extension(extension)


class ExoAppRunner(Exo):
    extensions: ExoAppExtensions

    def __call__(self, *args, **kwargs) -> Awaitable:
        return self.run(*args, **kwargs)

    async def run(self, *args, **kwargs):
        """ Calls the run method on all extensions that have been added. """
        return await asyncio.gather(*[extension.run() for extension in self.extensions])


class ExoApp(Exo):
    extensions: ExoAppExtensions
    run: ExoAppRunner

    def __init__(self, extensions: Sequence[Union[Type[GenericExo], Extension]]):
        self.extensions.load_extensions(extensions)
