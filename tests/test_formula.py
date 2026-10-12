from __future__ import annotations

import importlib.metadata
import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest
from packaging.requirements import Requirement

ROOT = Path(__file__).parent.parent
PYPROJECT_0_0_1 = '[project]\nname = "jumble-cli"\nversion = "0.0.1"\n'


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("formula", ROOT / "scripts" / "formula.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["formula"] = module  # dataclasses look their module up
    spec.loader.exec_module(module)
    return module


formula = _load()


def test_render() -> None:
    jumble = formula.Sdist("jumble-cli", "https://files/jumble_cli-0.1.0.tar.gz", "a" * 64)
    text = formula.render(
        jumble,
        [
            formula.Sdist("tomlkit", "https://files/tomlkit-0.15.1.tar.gz", "c" * 64),
            formula.Sdist("textual", "https://files/textual-8.2.8.tar.gz", "b" * 64),
        ],
    )
    assert text.startswith("class Jumble < Formula\n  include Language::Python::Virtualenv\n")
    assert '  url "https://files/jumble_cli-0.1.0.tar.gz"\n  sha256 "' + "a" * 64 in text
    assert '  depends_on "python@3.14"\n' in text
    assert text.index('resource "textual"') < text.index('resource "tomlkit"')
    assert '    url "https://files/tomlkit-0.15.1.tar.gz"\n    sha256 "' + "c" * 64 in text
    assert 'assert_match "jumble #{version}", shell_output("#{bin}/jumble --version")' in text
    digits = 'shell_output("#{bin}/jumble --no-config -n 8 -s digits")'
    assert f"assert_match(/\\A[0-9]{{8}}\\n\\z/, {digits})" in text
    assert text.endswith("  end\nend\n")


def test_platform_markers() -> None:
    def needed(line: str) -> bool:
        return formula.needed(Requirement(line), "3.14")

    assert needed("rich==15.0.0")
    assert needed("appnope==0.1.4 ; sys_platform == 'darwin'")
    assert not needed("colorama==0.4.6 ; sys_platform == 'win32'")
    assert not needed("tomli==2.2.1 ; python_full_version < '3.11'")


def test_pins_are_the_locked_runtime_dependencies() -> None:
    pins = {r.name: str(r.specifier) for r in formula.pins()}
    assert pins["textual"].startswith("==")
    assert pins["tomlkit"].startswith("==")
    assert "pytest" not in pins  # dev dependencies stay out
    assert "jumble-cli" not in pins


def test_checkout_version(tmp_path: Path) -> None:
    assert formula.checkout_version() == importlib.metadata.version("jumble-cli")
    (tmp_path / "pyproject.toml").write_text(PYPROJECT_0_0_1)
    assert formula.checkout_version(tmp_path) == "0.0.1"


def test_refuses_another_versions_checkout(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(PYPROJECT_0_0_1)
    with pytest.raises(SystemExit, match=r"is 0\.0\.1, not 0\.1\.0"):
        formula.main(["0.1.0", "--root", str(tmp_path)])
