"""Generate random strings from named character sets.

The behavior is defined in docs/spec.md; section numbers below refer to it.
"""

import secrets
import string
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass


def _span(first: int, last: int, *, without: Iterable[int] = ()) -> str:
    """The code points `first` through `last` inclusive, less those in `without`."""
    skip = set(without)
    return "".join(chr(c) for c in range(first, last + 1) if c not in skip)


def _cards() -> str:
    # Four suits of U+1Fxx1–U+1FxxE, each without its knight, U+1FxxC (§2.1).
    return "".join(
        _span(base + 0x1, base + 0xE, without=[base + 0xC])
        for base in range(0x1F0A0, 0x1F0E0, 0x10)
    )


# The named sets of §2.1. Insertion order is the canonical order (§2.4).
CHARSETS: dict[str, str] = {
    "lower": string.ascii_lowercase,
    "upper": string.ascii_uppercase,
    "digits": string.digits,
    "symbols": string.punctuation,  # DEC-2
    "space": " ",
    "chess": _span(0x2654, 0x265F),
    "cards": _cards(),
    "dice": _span(0x2680, 0x2685),
    "emoji-faces": _span(0x1F600, 0x1F64F),
    "emoji-animals": _span(0x1F400, 0x1F43E),
    "emoji-food": _span(0x1F345, 0x1F37B),
    "greek": _span(0x0391, 0x03A9, without=[0x03A2]) + _span(0x03B1, 0x03C9, without=[0x03C2]),
    "cyrillic": _span(0x0410, 0x044F),
    "latin-accented": _span(0x00C0, 0x00FF, without=[0x00D7, 0x00F7]),
    "arrows": _span(0x2190, 0x2199),
    "math": "±×÷∞≠≈≤≥√∑∏∫∂∆∇∈∉∩∪⊂⊃∀∃¬∧∨",
    "currency": "¢£¥€₹₽₩₪₺₿₫₱",
    "box": _span(0x2500, 0x259F),
}

# Look-alike characters left out by `no_ambiguous` (§3.1, DEC-3).
AMBIGUOUS: frozenset[str] = frozenset("0Ool1I|`'\";:.,-")

CUSTOM = "custom"

# Unicode categories custom characters may not use (§2.3, DEC-4).
_FORBIDDEN_CATEGORIES = frozenset({"Cc", "Cf", "Cs", "Co", "Cn"})


class JumbleError(ValueError):
    """Settings that can't produce strings; the text is a §6 message."""


@dataclass(frozen=True)
class Settings:
    """The settings every front end shares (§1, DEC-10).

    Holds what it was given, unchecked; `validate` judges it.
    """

    length: int = 16
    count: int = 1
    charsets: tuple[str, ...] = ("lower", "upper", "digits")
    custom: str = ""
    no_ambiguous: bool = False
    each: bool = False
    no_repeat: bool = False
    unique: bool = False


def _custom_chars(custom: str) -> str:
    """`custom` with repeats removed, each kept at its first position (§2.3)."""
    for c in custom:
        category = unicodedata.category(c)
        if category in _FORBIDDEN_CATEGORIES or category.startswith("M"):
            raise JumbleError("custom characters can't include control or combining characters")
    return "".join(dict.fromkeys(custom))


def chosen_sets(settings: Settings) -> list[tuple[str, str]]:
    """The chosen sets after §2.4 steps 1–3, as `(name, characters)` pairs.

    Named sets come in canonical order, then `custom` when it is non-empty.
    Runs the §6 checks from "unknown set name" to "a chosen set is empty", in
    that order.
    """
    for name in settings.charsets:
        if name not in CHARSETS:
            raise JumbleError(f"unknown character set: '{name}'")
    custom = _custom_chars(settings.custom)
    if not settings.charsets and not custom:
        raise JumbleError("choose at least one character set")

    chosen = set(settings.charsets)
    sets = [(name, chars) for name, chars in CHARSETS.items() if name in chosen]
    if custom:
        sets.append((CUSTOM, custom))

    result: list[tuple[str, str]] = []
    seen: set[str] = set()
    for name, chars in sets:
        kept = "".join(
            c for c in chars if c not in seen and not (settings.no_ambiguous and c in AMBIGUOUS)
        )
        if not kept:
            if name == CUSTOM:
                raise JumbleError("custom characters are all left out or already chosen")
            raise JumbleError(f"{name} has no characters left")
        seen.update(kept)
        result.append((name, kept))
    return result


def alphabet(charsets: Iterable[str], *, exclude_ambiguous: bool = False) -> str:
    """Join the named character sets into one alphabet, without duplicates."""
    chars: dict[str, None] = {}
    for name in charsets:
        if name not in CHARSETS:
            raise ValueError(f"unknown character set: {name!r}")
        chars.update(dict.fromkeys(CHARSETS[name]))
    if exclude_ambiguous:
        chars = {c: None for c in chars if c not in AMBIGUOUS}
    if not chars:
        raise ValueError("no characters to choose from")
    return "".join(chars)


def generate(
    length: int = 16,
    charsets: Iterable[str] = ("lower", "upper", "digits"),
    *,
    exclude_ambiguous: bool = False,
) -> str:
    """Return a random string of `length` characters, using `secrets` (DEC-1)."""
    if length < 1:
        raise ValueError("length must be at least 1")
    chars = alphabet(charsets, exclude_ambiguous=exclude_ambiguous)
    return "".join(secrets.choice(chars) for _ in range(length))
