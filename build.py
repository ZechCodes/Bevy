from os import getenv
from pathlib import Path
from subprocess import Popen
from sys import argv, stdout, stderr, stdin


packages = argv[1:] or [""]
if "bevy" in packages:
    packages.remove("bevy")
    packages.append("")

path = Path().parent
bevy_path = path / "bevy"
for package in packages:
    package_toml = bevy_path / package / "pyproject.toml"
    if not package_toml.is_file():
        print(f"\u001b[31mERROR: {package_toml} was not found\u001b[0m")
        continue

    (path / "pyproject.toml").unlink()
    package_toml.link_to(path / "pyproject.toml")
    process = Popen(
        [
            "poetry",
            "publish",
            "--build",
            "-u",
            getenv("PYPI_USERNAME"),
            "-p",
            getenv("PYPI_PASSWORD"),
        ],
        stdout=stdout,
        stderr=stderr,
        stdin=stdin,
    )
    process.wait()
