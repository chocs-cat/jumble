"""The settings file (docs/spec.md §5).

Reading only; section numbers below refer to the spec.
"""

import os
import tomllib
from dataclasses import fields
from pathlib import Path

from jumble.generate import JumbleError, Settings, check_value

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
