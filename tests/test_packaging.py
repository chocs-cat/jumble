"""Every copy of the distribution's name agrees (DEC-24)."""

import json
import tomllib
from pathlib import Path

from jumble.cli import DISTRIBUTION

ROOT = Path(__file__).parent.parent


def toml(name: str) -> dict:
    return tomllib.loads((ROOT / name).read_text())


def test_the_distribution_is_jumble_cli() -> None:
    assert toml("pyproject.toml")["project"]["name"] == DISTRIBUTION == "jumble-cli"


def test_release_please_names_the_distribution() -> None:
    [package] = json.loads((ROOT / "release-please-config.json").read_text())["packages"].values()
    assert package["package-name"] == "jumble-cli"
    [lock] = [f for f in package["extra-files"] if f["path"] == "uv.lock"]
    assert "=='jumble-cli'" in lock["jsonpath"]


def test_the_lock_pins_the_project_at_its_version() -> None:
    [project] = [p for p in toml("uv.lock")["package"] if p["name"] == "jumble-cli"]
    assert project["version"] == toml("pyproject.toml")["project"]["version"]


def test_the_command_and_the_import_package_stay_jumble() -> None:
    pyproject = toml("pyproject.toml")
    assert pyproject["project"]["scripts"] == {"jumble": "jumble:main"}
    assert pyproject["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"] == ["src/jumble"]
