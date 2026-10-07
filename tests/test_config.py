import tomllib
from pathlib import Path

import pytest

from jumble.config import config_path, load
from jumble.generate import JumbleError

# config_path tests set the variables themselves; load tests take paths.


def test_path_from_jumble_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JUMBLE_CONFIG", "some/where.toml")
    monkeypatch.setenv("XDG_CONFIG_HOME", "/xdg")
    assert config_path() == Path("some/where.toml")


def test_empty_jumble_config_falls_through(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JUMBLE_CONFIG", "")
    monkeypatch.setenv("XDG_CONFIG_HOME", "/xdg")
    assert config_path() == Path("/xdg/jumble/config.toml")


def test_path_from_absolute_xdg(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("JUMBLE_CONFIG")
    monkeypatch.setenv("XDG_CONFIG_HOME", "/xdg")
    assert config_path() == Path("/xdg/jumble/config.toml")


@pytest.mark.parametrize("xdg", ["relative/xdg", ""])
def test_relative_or_empty_xdg_falls_through(
    xdg: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("JUMBLE_CONFIG")
    monkeypatch.setenv("XDG_CONFIG_HOME", xdg)
    monkeypatch.setenv("HOME", str(tmp_path))
    assert config_path() == tmp_path / ".config/jumble/config.toml"


def test_path_from_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("JUMBLE_CONFIG")
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    assert config_path() == tmp_path / ".config/jumble/config.toml"


def test_missing_file_is_empty(config_file: Path) -> None:
    assert load(config_file) == {}


def test_all_eight_keys(config_file: Path) -> None:
    config_file.write_text(
        'unique = true\nlength = 32\ncount = 5\ncharsets = ["digits", "greek"]\n'
        'custom = "ab"\nno_ambiguous = true\neach = true\nno_repeat = true\n'
    )
    loaded = load(config_file)
    assert loaded == {
        "unique": True,
        "length": 32,
        "count": 5,
        "charsets": ["digits", "greek"],
        "custom": "ab",
        "no_ambiguous": True,
        "each": True,
        "no_repeat": True,
    }
    assert list(loaded)[:2] == ["unique", "length"]  # file order


def error(path: Path) -> str:
    with pytest.raises(JumbleError) as e:
        load(path)
    return str(e.value)


def test_unreadable(config_file: Path) -> None:
    config_file.mkdir()
    assert error(config_file) == f"can't read {config_file}: Is a directory"


def test_not_utf8(config_file: Path) -> None:
    config_file.write_bytes(b"\xff")
    assert error(config_file) == f"{config_file}: invalid TOML: not UTF-8"


def test_not_toml(config_file: Path) -> None:
    config_file.write_text("length = ")
    msg = error(config_file)
    assert msg.startswith(f"{config_file}: invalid TOML: ")
    # DETAIL is str() of tomllib's own error.
    with pytest.raises(tomllib.TOMLDecodeError) as e:
        tomllib.loads("length = ")
    assert msg == f"{config_file}: invalid TOML: {e.value}"


def test_unknown_key(config_file: Path) -> None:
    config_file.write_text("colour = 1\n")
    assert error(config_file) == f"{config_file}: colour: unknown setting"


@pytest.mark.parametrize(
    ("line", "key", "word"),
    [
        ("length = true", "length", "an integer"),
        ("length = 16.0", "length", "an integer"),
        ("count = true", "count", "an integer"),
        ('charsets = "lower"', "charsets", "a list of set names"),
        ("charsets = [1]", "charsets", "a list of set names"),
        ('charsets = ["lower", 1]', "charsets", "a list of set names"),
        ("custom = 1", "custom", "a string"),
        ("each = 1", "each", "a boolean"),
        ('no_ambiguous = "yes"', "no_ambiguous", "a boolean"),
        ("no_repeat = 0", "no_repeat", "a boolean"),
        ("unique = []", "unique", "a boolean"),
    ],
)
def test_wrong_type(config_file: Path, line: str, key: str, word: str) -> None:
    config_file.write_text(line + "\n")
    assert error(config_file) == f"{config_file}: {key}: must be {word}"


@pytest.mark.parametrize(
    ("line", "key", "message"),
    [
        ("length = 0", "length", "length must be at least 1"),
        ("count = 0", "count", "count must be at least 1"),
        ('charsets = ["foo"]', "charsets", "unknown character set: 'foo'"),
        ('charsets = [""]', "charsets", "unknown character set: ''"),
        (
            'custom = "á"',
            "custom",
            "custom characters can't include control or combining characters",
        ),
    ],
)
def test_rule_rejects_value(config_file: Path, line: str, key: str, message: str) -> None:
    config_file.write_text(line + "\n", encoding="utf-8")
    assert error(config_file) == f"{config_file}: {key}: {message}"


def test_first_error_in_file_order(config_file: Path) -> None:
    config_file.write_text("colour = 1\nlength = 0\n")
    assert error(config_file) == f"{config_file}: colour: unknown setting"
    config_file.write_text("length = 0\ncolour = 1\n")
    assert error(config_file) == f"{config_file}: length: length must be at least 1"


def test_rules_between_settings_are_not_file_errors(config_file: Path) -> None:
    # Checked on the effective settings instead (§5.1, DEC-17).
    config_file.write_text("each = true\nlength = 2\n")
    assert load(config_file) == {"each": True, "length": 2}


def test_path_is_shown_as_resolved(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    Path("rel.toml").write_text("length = 0\n")
    monkeypatch.setenv("JUMBLE_CONFIG", "rel.toml")
    assert error(config_path()) == "rel.toml: length: length must be at least 1"
