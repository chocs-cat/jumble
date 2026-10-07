import tomllib
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
import tomlkit
from tomlkit.exceptions import KeyAlreadyPresent

from jumble.config import TEMPLATE, config_path, file_settings, load, save
from jumble.generate import JumbleError, Settings, settings_dict

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


# save (§5.3, DEC-18).

SPEC = Path(__file__).parents[1] / "docs" / "spec.md"


def test_template_is_the_specs() -> None:
    text = SPEC.read_text(encoding="utf-8")
    after = text.split("The template, with the saved values", 1)[1]
    block = after.split("```toml\n", 1)[1].split("```", 1)[0]
    assert block == TEMPLATE


def template(**values: str) -> str:
    """TEMPLATE with each `KEY = VALUE` line's value replaced."""
    lines = list[str](TEMPLATE.splitlines(keepends=True))
    for key, value in values.items():
        [i] = [i for i, line in enumerate(lines) if line.startswith(f"{key} = ")]
        lines[i] = f"{key} = {value}\n"
    return "".join(lines)


EVERY = Settings(
    length=32,
    count=5,
    charsets=("greek", "digits", "lower"),  # not canonical: written canonical
    custom='a"b\\c🐀',
    no_ambiguous=True,
    each=True,
    no_repeat=True,
    unique=True,
)


def test_missing_file_and_directories(tmp_path: Path) -> None:
    path = tmp_path / "a" / "b" / "config.toml"
    save(path, EVERY)
    assert path.read_text(encoding="utf-8") == template(
        length="32",
        count="5",
        charsets='["lower", "digits", "greek"]',
        custom='"a\\"b\\\\c🐀"',
        no_ambiguous="true",
        each="true",
        no_repeat="true",
        unique="true",
    )
    loaded = load(path)
    assert loaded == settings_dict(EVERY)
    assert list(loaded) == list(settings_dict(EVERY))  # all eight, §1's order


def test_defaults_to_a_missing_file_are_the_template(tmp_path: Path) -> None:
    path = tmp_path / "a" / "b" / "config.toml"
    save(path, Settings())
    assert path.read_bytes() == TEMPLATE.encode()


def test_only_custom_is_an_empty_list(config_file: Path) -> None:
    save(config_file, Settings(charsets=(), custom="ab"))
    assert config_file.read_text() == template(charsets="[]", custom='"ab"')
    assert load(config_file)["charsets"] == []


def test_saving_twice_changes_nothing(config_file: Path) -> None:
    save(config_file, EVERY)
    first = config_file.read_bytes()
    save(config_file, EVERY)
    assert config_file.read_bytes() == first


# Every key at its default, laid out as no template would: no spaces, a
# literal string, a padded array, comments everywhere.
HAND_WRITTEN = """\
#top
length=16
  count = 1 # one
charsets = [ "lower","upper",
  "digits" ]  # the usual
custom = ''
no_ambiguous = false
each    = false
# below
no_repeat = false
unique = false"""


def test_nothing_changed_is_byte_for_byte(config_file: Path) -> None:
    config_file.write_text(HAND_WRITTEN)
    save(config_file, Settings())
    assert config_file.read_text() == HAND_WRITTEN


COMMENTED = """\
# My settings.

# How long.
length = 20  # long enough
# How many.
count = 3  # a few
charsets = ["lower", "digits"]  # no capitals
custom = "!?"  # punctuation
no_ambiguous = true  # readable
each = true  # mixed
no_repeat = false  # repeats are fine
unique = false  # whatever
"""
SAVED = Settings(
    length=20, count=3, charsets=("lower", "digits"), custom="!?", no_ambiguous=True, each=True
)


@pytest.mark.parametrize(
    ("change", "line"),
    [
        ({"length": 24}, "length = 24  # long enough"),
        ({"count": 1}, "count = 1  # a few"),
        ({"charsets": ("lower",)}, 'charsets = ["lower"]  # no capitals'),
        ({"custom": ""}, 'custom = ""  # punctuation'),
        ({"no_ambiguous": False}, "no_ambiguous = false  # readable"),
        ({"each": False}, "each = false  # mixed"),
        ({"no_repeat": True}, "no_repeat = true  # repeats are fine"),
        ({"unique": True}, "unique = true  # whatever"),
    ],
)
def test_one_changed_value_changes_one_line(
    config_file: Path, change: dict[str, Any], line: str
) -> None:
    config_file.write_text(COMMENTED)
    save(config_file, replace(SAVED, **change))
    before = COMMENTED.splitlines()
    after = config_file.read_text().splitlines()
    assert len(after) == len(before)
    changed = [i for i, (a, b) in enumerate(zip(before, after, strict=True)) if a != b]
    assert len(changed) == 1
    assert after[changed[0]] == line


@pytest.mark.parametrize(
    ("key", "old", "settings", "new"),
    [
        # Equal under a plain `==` but not in type, so a plain comparison
        # would leave each of these lines as it is.
        ("length", "true", Settings(length=1), "1"),
        ("count", "true", Settings(count=1), "1"),
        ("length", "16.0", Settings(length=16), "16"),
        ("each", "0", Settings(each=False), "false"),
        ("unique", "1", Settings(unique=True), "true"),
    ],
)
def test_same_value_of_another_type_is_replaced(
    config_file: Path, key: str, old: str, settings: Settings, new: str
) -> None:
    config_file.write_text(template(**{key: f"{old}  # kept"}))
    save(config_file, settings)
    assert config_file.read_text() == template(**{key: f"{new}  # kept"})


def test_unknown_keys_and_tables_are_removed(config_file: Path) -> None:
    config_file.write_text(TEMPLATE + "colour = 1\n[extra]\nx = 1\n[extra.deeper]\ny = 2\n")
    save(config_file, Settings())
    assert config_file.read_text() == TEMPLATE


def test_a_setting_holding_a_table_is_replaced(config_file: Path) -> None:
    config_file.write_text("count = 1\n[length]\nx = 1\n")
    save(config_file, Settings())
    assert load(config_file) == settings_dict(Settings())


def test_missing_key_is_appended_at_the_end(config_file: Path) -> None:
    without = TEMPLATE.replace('# Extra characters, drawn as one more set.\ncustom = ""\n', "")
    config_file.write_text(without)
    save(config_file, Settings())
    assert config_file.read_text() == without + 'custom = ""\n'


def test_missing_keys_are_appended_in_settings_order(config_file: Path) -> None:
    config_file.write_text("unique = true\n")
    save(config_file, Settings(unique=True))
    assert config_file.read_text() == (
        'unique = true\nlength = 16\ncount = 1\ncharsets = ["lower", "upper", "digits"]\n'
        'custom = ""\nno_ambiguous = false\neach = false\nno_repeat = false\n'
    )


@pytest.mark.parametrize(
    "data",
    [
        b"\xff",
        b"length = ",
        b"length = 1\nlength = 2\n",
        # TOML 1.1, which tomlkit reads as `custom = "A"` and tomllib rejects:
        # kept as equal, the line would break `load` (DEC-19).
        b'custom = "\\x41"\n',
    ],
)
def test_unreadable_toml_becomes_the_template(config_file: Path, data: bytes) -> None:
    config_file.write_bytes(data)
    save(config_file, Settings(length=32, custom="A"))
    assert config_file.read_text() == template(length="32", custom='"A"')
    assert load(config_file)["custom"] == "A"


def test_toml_only_tomlkit_rejects_becomes_the_template(
    config_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # No such file is known; should tomlkit refuse one tomllib reads, the save
    # starts over rather than crash, as for any other unreadable TOML.
    parse = tomlkit.parse

    def refuse(text: str) -> tomlkit.TOMLDocument:
        if text != TEMPLATE:
            raise KeyAlreadyPresent("length")
        return parse(text)

    monkeypatch.setattr(tomlkit, "parse", refuse)
    config_file.write_text("length = 20\n")
    save(config_file, Settings(length=32))
    assert config_file.read_text() == template(length="32")


def test_symlink_is_written_through(tmp_path: Path) -> None:
    target = tmp_path / "real.toml"
    target.write_text(TEMPLATE)
    link = tmp_path / "link.toml"
    link.symlink_to(target)
    save(link, Settings(length=32))
    assert link.is_symlink()
    assert link.readlink() == target
    assert target.read_text() == template(length="32")


def test_permissions_are_kept(config_file: Path) -> None:
    config_file.write_text(TEMPLATE)
    config_file.chmod(0o640)
    save(config_file, Settings(length=32))
    assert config_file.stat().st_mode & 0o777 == 0o640
    assert config_file.read_text() == template(length="32")


def save_error(path: Path) -> str:
    with pytest.raises(JumbleError) as e:
        save(path, Settings())
    return str(e.value)


def test_directory_cant_be_saved(config_file: Path) -> None:
    config_file.mkdir()
    assert save_error(config_file) == f"can't save {config_file}: Is a directory"


def test_unreadable_file_cant_be_saved(config_file: Path) -> None:
    # The read fails, not the write: the file is not replaced.
    config_file.write_text("length = 32\n")
    config_file.chmod(0o200)
    try:
        assert save_error(config_file) == f"can't save {config_file}: Permission denied"
    finally:
        config_file.chmod(0o600)
    assert config_file.read_text() == "length = 32\n"


def test_read_only_file_cant_be_saved(config_file: Path) -> None:
    config_file.write_text("length = 32\n")
    config_file.chmod(0o444)
    try:
        assert save_error(config_file) == f"can't save {config_file}: Permission denied"
    finally:
        config_file.chmod(0o644)
    assert config_file.read_text() == "length = 32\n"


def test_save_path_is_shown_as_given(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    Path("rel.toml").mkdir()
    # As pathlib writes it: no leading `./`, not made absolute (§5.1).
    assert save_error(Path("./rel.toml")) == "can't save rel.toml: Is a directory"


# file_settings: the file over the built-in defaults, as §5.2 merges them.


@pytest.mark.parametrize(
    ("file", "expected"),
    [
        ({}, Settings()),
        ({"charsets": []}, Settings()),
        ({"custom": ""}, Settings()),
        ({"length": 24, "custom": "abc"}, Settings(length=24, charsets=(), custom="abc")),
        ({"charsets": ["digits"]}, Settings(charsets=("digits",))),
        ({"each": True, "count": 3}, Settings(count=3, each=True)),
    ],
)
def test_file_settings(file: dict[str, Any], expected: Settings) -> None:
    assert file_settings(file) == expected
