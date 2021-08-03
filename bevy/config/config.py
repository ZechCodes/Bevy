from bevy.config.loader import Loader
from bevy.config.config_file import ConfigFile
from bevy.config.exceptions import NoLoadersRegistered, NoResolversRegistered
from bevy.config.resolver import Resolver, Reader
from bevy.config.section_loader import SectionLoader
from typing import Optional, Sequence, Type


class Config:
    def __init__(
        self,
        default_filename: str = "config",
        loaders: Sequence[Type[Loader]] = tuple(),
        resolvers: Sequence[Resolver] = tuple(),
    ):
        self._default_filename = default_filename
        self._loaders = set(loaders)
        self._resolvers = set(resolvers)
        self._supported_file_types = tuple()

    @property
    def supported_file_types(self) -> tuple[str]:
        """A tuple of file extensions that the config has loaders for."""
        if not self._supported_file_types:
            self._supported_file_types = sum(
                (loader.file_types for loader in self._loaders), tuple()
            )
        return self._supported_file_types

    def get_config_file(self, filename: Optional[str] = None) -> ConfigFile:
        """Searches all resolvers for a file matching the filename and returns a ConfigFile object for accessing
        sections. If no filename is given it will fallback to using the default set on the Config object, this is often
        just "config". The filename should not contain an extension, the extension will be determined by the loaded
        loaders and by what the resolvers are able to find.

        This function will raise:
        - bevy.extensions.config.exceptions.NoLoadersRegistered
          If no loaders have been registered.
        - bevy.extensions.config.exceptions.NoResolversRegistered
          If no resolvers have been registered.
        - FileNotFound
          If no resolver is able to find a matching config file with a supported extension.
        - ValueError
          If no loaders match the file type given by the Reader returned by the resolvers.
        """
        if not self._loaders:
            raise NoLoadersRegistered(
                "You must register a file loader in order to load config files"
            )

        if not self._resolvers:
            raise NoResolversRegistered(
                "You must register a file resolver in order to find config files"
            )

        filename = filename if filename else self._default_filename
        reader = self._find_file_reader(filename)
        loader = self._find_file_type_loader(reader)
        return ConfigFile(loader)

    def get_section(self, section_name: str, filename: Optional[str] = None):
        config = self.get_config_file(filename)
        return config.get_section(section_name)

    def add_resolver(self, resolver: Resolver):
        self._resolvers.add(resolver)

    def remove_resolver(self, resolver: Resolver):
        self._resolvers.remove(resolver)

    def add_loader(self, loader: Loader):
        """Adds a loader to the config manager and invalidates the supported file types cache."""
        self._loaders.add(loader)
        self._supported_file_types = tuple()

    def remove_loader(self, loader: Loader):
        """Removes a loader from the config manager and invalidates the supported file types cache."""
        self._loaders.remove(loader)
        self._supported_file_types = tuple()

    def _find_file_reader(self, filename: str) -> Reader:
        for resolver in self._resolvers:
            reader = resolver.get_file_reader(filename, self.supported_file_types)
            if reader:
                return reader

        raise FileNotFoundError(
            f"Could not find find a file that matched {filename!r}, looked for these file types: "
            f"{', '.join(self.supported_file_types) if self.supported_file_types else 'No file types set by loaders'}"
        )

    def _find_file_type_loader(self, reader: Reader) -> Loader:
        for loader in self._loaders:
            if reader.file_type in loader.file_types:
                return loader(reader)

        raise ValueError(
            f"Could not find a loader that matched the file type {reader.file_type!r}, looked for these file types: "
            f"{', '.join(self.supported_file_types) if self.supported_file_types else 'No file types set by loaders'}"
        )

    def __class_getitem__(cls, item) -> SectionLoader:
        section = item[0] if isinstance(item, tuple) else item
        filename = item[1] if len(item) == 2 else None
        return SectionLoader(section, filename)
