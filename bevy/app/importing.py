from importlib import machinery, util
from pathlib import Path
from typing import Any
import sys


def get_module_attr_from_path(path: Path, module_name: str, attr_name: str) -> Any:
    path = _get_module_path(path, module_name)
    module = import_module_from_path(module_name)
    return getattr(module, attr_name)


def import_module_from_path(path: Path, module: str):
    finder = machinery.FileFinder(
        str(path.resolve()),
        (
            machinery.SourceFileLoader,
            [".py"],
        ),
    )
    spec = finder.find_spec(module)
    if spec.name in sys.modules:
        return sys.modules[spec.name]

    module = util.module_from_spec(spec)
    sys.modules[spec.name] = module

    spec.loader.exec_module(module)
    return module


def _get_module_path(path: Path, module_name: str) -> Path:
    path = path / f"{module_name}.py"
    if not path.exists():
        path = path / module_name / "__init__.py"
    return path.resolve()
