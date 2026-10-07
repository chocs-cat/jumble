from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def config_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A settings file path under `tmp_path`, missing until a test writes it.

    `$JUMBLE_CONFIG` points here for every test, subprocesses included, so no
    test ever reads the real settings file.
    """
    path = tmp_path / "config.toml"
    monkeypatch.setenv("JUMBLE_CONFIG", str(path))
    return path
