from pathlib import Path
from typing import Union


class FileReader:
    def __init__(self, file_path: Union[Path, str]):
        self.file_path = Path(file_path)

        if not self.file_path.is_file():
            raise ValueError(
                f"The file reader must be given a path to a file, got {file_path!r}"
            )

    @property
    def file_type(self) -> str:
        return self.file_path.suffix[1:]

    def read(self) -> str:
        with self.file_path.open() as file:
            return file.read()

    def save(self, data: str):
        with self.file_path.open("w") as file:
            file.write(data)
