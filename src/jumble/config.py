"""The settings file (docs/spec.md §5): reading it, and saving over it.

Section numbers below refer to the spec.
"""

import os
import tomllib
from collections.abc import Mapping
from dataclasses import fields, replace
from pathlib import Path
from typing import Any

import tomlkit
from tomlkit.exceptions import TOMLKitError

from jumble.generate import JumbleError, Settings, check_value, settings_dict

# §1's setting names, in §1's order.
NAMES: tuple[str, ...] = tuple(f.name for f in fields(Settings))


def config_path() -> Path:
    """Where the settings file is (§5.1, DEC-10).

    `$JUMBLE_CONFIG` if set and not empty, as given; else
    `$XDG_CONFIG_HOME/jumble/config.toml` if that is an absolute path; else
    `~/.config/jumble/config.toml`, on macOS too.
    """
    if given := os.environ.get("JUMBLE_CONFIG"):
        return Path(given)
    xdg = Path(os.environ.get("XDG_CONFIG_HOME", ""))
    if xdg.is_absolute():
        return xdg / "jumble" / "config.toml"
    return Path.home() / ".config" / "jumble" / "config.toml"


def _type_word(name: str, value: object) -> str | None:
    """The §6 type word when `value` hasn't setting `name`'s type (§5.1), else None."""
    if name in ("length", "count"):
        # A TOML boolean is a Python bool, which is an int too: rule it out.
        ok = isinstance(value, int) and not isinstance(value, bool)
        return None if ok else "an integer"
    if name == "charsets":
        ok = isinstance(value, list) and all(isinstance(v, str) for v in value)
        return None if ok else "a list of set names"
    if name == "custom":
        return None if isinstance(value, str) else "a string"
    return None if isinstance(value, bool) else "a boolean"


def load(path: Path) -> dict[str, object]:
    """The settings file at `path`, as its keys and values in the file's order.

    A missing file is `{}`. Anything else wrong raises `JumbleError` with the
    §6 settings-file message for the first error, checked in §5.1's order:
    reading, then UTF-8 and TOML, then each key's name, type, and own rule.
    Rules that relate settings to each other are left to `validate` (DEC-17).
    """
    try:
        data = path.read_bytes()
    except FileNotFoundError:
        return {}
    except OSError as e:
        raise JumbleError(f"can't read {path}: {e.strerror}") from e
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as e:
        raise JumbleError(f"{path}: invalid TOML: not UTF-8") from e
    try:
        table = tomllib.loads(text)
    except tomllib.TOMLDecodeError as e:
        raise JumbleError(f"{path}: invalid TOML: {e}") from e

    for key, value in table.items():
        if key not in NAMES:
            raise JumbleError(f"{path}: {key}: unknown setting")
        if word := _type_word(key, value):
            raise JumbleError(f"{path}: {key}: must be {word}")
        try:
            check_value(key, value)
        except JumbleError as e:
            raise JumbleError(f"{path}: {key}: {e}") from e
    return table


def file_settings(file: Mapping[str, Any]) -> Settings:
    """The built-in defaults, then `file`'s keys, merged as §5.2 merges them (DEC-9).

    `file` is what `load` returned, or `{}`. `length`, `count`, and the four
    options go key by key. The characters go as a whole: a file that sets
    `charsets` or `custom` chooses with both, so `custom = "abc"` alone
    chooses no named set; the default sets apply only when neither chooses
    any. `cli.settings_from` lays the command line over the file and merges
    through here, and the settings screen fills its form from this (§7.4).
    """
    defaults = Settings()
    values = {key: file[key] for key in NAMES if key in file}
    charsets = tuple(values.pop("charsets", ()))
    custom = values.pop("custom", "")
    if not charsets and not custom:
        # Nothing chose any characters, so the default sets apply (§1, DEC-9).
        charsets = defaults.charsets
    return replace(defaults, **values, charsets=charsets, custom=custom)


# A new file starts from this, with the saved values in place of these
# defaults (§5.3); a test holds it to the spec's copy.
TEMPLATE = """\
# jumble settings. Every key is optional; options given on the command
# line override them. See `jumble --help` for the character sets.

# Characters per string, at least 1.
length = 16
# How many strings, at least 1.
count = 1
# The named sets to draw from.
charsets = ["lower", "upper", "digits"]
# Extra characters, drawn as one more set.
custom = ""
# Leave out look-alike characters such as 0 O l 1 I.
no_ambiguous = false
# At least one character from every chosen set.
each = false
# No character twice within a string.
no_repeat = false
# No string twice in the output.
unique = false
"""


def _document(path: Path) -> tomlkit.TOMLDocument:
    """The file at `path` to save over, or the template in its place (§5.3 step 1).

    A missing file, or one that is not UTF-8 or not valid TOML, is replaced
    by the template; a file that exists but can't be read raises `JumbleError`.
    """
    try:
        data = path.read_bytes()
    except FileNotFoundError:
        return tomlkit.parse(TEMPLATE)
    except OSError as e:
        raise JumbleError(f"can't save {path}: {e.strerror}") from e
    try:
        text = data.decode("utf-8")
        # Valid TOML is what `load` reads: tomlkit also parses TOML 1.1, which
        # tomllib rejects, and a line kept from such a file would still break
        # the command line (DEC-19).
        tomllib.loads(text)
        return tomlkit.parse(text)
    except (UnicodeDecodeError, tomllib.TOMLDecodeError, TOMLKitError):
        return tomlkit.parse(TEMPLATE)


def save(path: Path, settings: Settings) -> None:
    """Write `settings` to the settings file at `path`, keeping what it can (§5.3, DEC-18).

    Unknown keys are removed; a key whose value already equals the saved one,
    in TOML type and value, is left as it is, comments and all; any other is
    replaced on its own line, and a missing one is appended. The write is in
    place, through a symlink, after creating missing parent directories. A
    file that can't be read or written raises `JumbleError` with
    `can't save PATH: REASON` (§7.4). Pass settings that have passed
    `validate`.
    """
    doc = _document(path)
    for key in [key for key in doc if key not in NAMES]:
        del doc[key]
    for key, value in settings_dict(settings).items():
        if key in doc:
            old = doc.item(key).unwrap()
            # Same type, then same value: `True == 1` and `16.0 == 16` would
            # otherwise leave `length = true` and `length = 16.0` in place.
            if type(old) is type(value) and old == value:
                continue
        # Replaces the value in place, keeping the line's comment, or appends
        # `KEY = VALUE` at the end.
        doc[key] = value
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(tomlkit.dumps(doc).encode("utf-8"))
    except OSError as e:
        raise JumbleError(f"can't save {path}: {e.strerror}") from e
