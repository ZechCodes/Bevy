from bevy.config.file_reader import FileReader
from pathlib import Path
from typing import Optional, Union


class DirectoryResolver:
    def __init__(self, directory: Union[Path, str]):
        self.directory = Path(directory)

        if not self.directory.is_dir():
            self.directory = self.directory.parent

    def get_file_reader(
        self, filename: str, file_types: tuple[str]
    ) -> Optional[FileReader]:
        for item in self.directory.iterdir():
            if item.is_file() and item.suffix[1:] in file_types:
                return FileReader(item)
