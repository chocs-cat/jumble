"""Generate random strings from named character sets.

The behavior is defined in docs/spec.md; section numbers below refer to it.
"""

import math
import secrets
import string
import unicodedata
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from typing import NamedTuple


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

# Look-alike characters left out by `no_ambiguous`, in §3.1's order (DEC-3).
LOOK_ALIKES = "0Ool1I|`'\";:.,-"
AMBIGUOUS: frozenset[str] = frozenset(LOOK_ALIKES)

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


def settings_dict(settings: Settings) -> dict[str, object]:
    """`settings` as §1's eight values, keyed by setting name in §1's order (DEC-10).

    `charsets` lists each chosen named set once, in canonical order; `custom`
    is the string as given (§4.2). Unknown set names are dropped, so pass
    settings that have passed `validate`.
    """
    values = asdict(settings)
    chosen = set(settings.charsets)
    values["charsets"] = [name for name in CHARSETS if name in chosen]
    return values


def _custom_chars(custom: str) -> str:
    """`custom` with repeats removed, each kept at its first position (§2.3)."""
    for c in custom:
        category = unicodedata.category(c)
        if category in _FORBIDDEN_CATEGORIES or category.startswith("M"):
            raise JumbleError("custom characters can't include control or combining characters")
    return "".join(dict.fromkeys(custom))


def check_names(charsets: Iterable[str]) -> None:
    """Raise §6's `unknown character set: 'NAME'` for the first name not in `CHARSETS`.

    An empty name (from `-s lower,`) is unknown too (§2.2).
    """
    for name in charsets:
        if name not in CHARSETS:
            raise JumbleError(f"unknown character set: '{name}'")


def chosen_sets(settings: Settings) -> list[tuple[str, str]]:
    """The chosen sets after §2.4 steps 1–3, as `(name, characters)` pairs.

    Named sets come in canonical order, then `custom` when it is non-empty.
    Runs the §6 checks from "unknown set name" to "a chosen set is empty", in
    that order.
    """
    check_names(settings.charsets)
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


class Strength(NamedTuple):
    """Alphabet size and strength of a settings value (§3.5)."""

    alphabet_size: int
    bits: float
    """log₂ of the number of possible strings, unrounded."""
    is_bound: bool
    """True when `each` is on: the bits are then an upper bound (DEC-7)."""


def strength_line(strength: Strength) -> str:
    """The strength line of §4.3, shared by `--strength` and the TUI's subtitle.

    For example `62 characters · 95.3 bits per string`, with `at most` before
    the bits when they are a bound.
    """
    size = strength.alphabet_size
    chars = "1 character" if size == 1 else f"{size} characters"
    bound = "at most " if strength.is_bound else ""
    return f"{chars} · {bound}{strength.bits:.1f} bits per string"


def _possible(size: int, settings: Settings) -> int:
    """The number of possible strings, P (§3.5); ignores `each` (DEC-7)."""
    if settings.no_repeat:
        return math.perm(size, settings.length)
    return size**settings.length


def validate(settings: Settings) -> list[tuple[str, str]]:
    """Run every §6 check before drawing, in the table's order; the first failure wins.

    Returns the chosen sets, as `chosen_sets` does.
    """
    if settings.length < 1:
        raise JumbleError("length must be at least 1")
    if settings.count < 1:
        raise JumbleError("count must be at least 1")
    sets = chosen_sets(settings)
    k = len(sets)
    size = sum(len(chars) for _, chars in sets)
    if settings.each and settings.length < k:
        raise JumbleError(
            f"length must be at least {k} to take one character from each of {k} sets"
        )
    if settings.no_repeat and settings.length > size:
        raise JumbleError(f"length can't be more than {size} without repeats")
    if settings.unique:
        possible = _possible(size, settings)
        if settings.count > possible:
            raise JumbleError(f"only {possible} different strings are possible")
    return sets


def strength(settings: Settings) -> Strength:
    """Alphabet size, bits per string, and whether that is a bound (§3.5).

    Validates first, so the alphabet is the one `generate` would use.
    """
    size = sum(len(chars) for _, chars in validate(settings))
    # log₂ of the exact integer, so a long string can't overflow a float power.
    bits = math.log2(_possible(size, settings))
    return Strength(size, bits, settings.each)


def _sample(pool: list[str], n: int) -> list[str]:
    """`n` distinct items of `pool`, by a partial Fisher–Yates shuffle (DEC-6). Reorders `pool`."""
    for i in range(n):
        j = i + secrets.randbelow(len(pool) - i)
        pool[i], pool[j] = pool[j], pool[i]
    return pool[:n]


def _shuffle(items: list[str]) -> None:
    """Shuffle `items` in place with Fisher–Yates (DEC-6)."""
    for i in range(len(items) - 1, 0, -1):
        j = secrets.randbelow(i + 1)
        items[i], items[j] = items[j], items[i]


def _draw(settings: Settings, sets: list[tuple[str, str]], alphabet: str) -> str:
    """One string of `settings.length` characters (§3.2, §3.3)."""
    length = settings.length
    if settings.each:
        chars = [s[secrets.randbelow(len(s))] for _, s in sets]
        rest = length - len(chars)
        if settings.no_repeat:
            # The sets are disjoint, so the picks are distinct already.
            picked = set(chars)
            chars += _sample([c for c in alphabet if c not in picked], rest)
        else:
            chars += [alphabet[secrets.randbelow(len(alphabet))] for _ in range(rest)]
        _shuffle(chars)
        return "".join(chars)
    if settings.no_repeat:
        return "".join(_sample(list(alphabet), length))
    return "".join(alphabet[secrets.randbelow(len(alphabet))] for _ in range(length))


def generate(settings: Settings) -> list[str]:
    """Validate `settings`, then draw `count` strings (§3).

    Every draw goes through `secrets.randbelow` (DEC-1, DEC-6). With `unique`,
    a repeat is drawn again, and after `max(100000, 20 × count)` draws without
    `count` distinct strings generation gives up (§3.4, DEC-7).
    """
    sets = validate(settings)
    alphabet = "".join(chars for _, chars in sets)
    if not settings.unique:
        return [_draw(settings, sets, alphabet) for _ in range(settings.count)]

    cap = max(100_000, 20 * settings.count)
    strings: dict[str, None] = {}  # keeps drawn order
    draws = 0
    while len(strings) < settings.count:
        if draws == cap:
            raise JumbleError(
                f"gave up after {cap} draws with {len(strings)} of {settings.count} unique strings"
            )
        strings[_draw(settings, sets, alphabet)] = None
        draws += 1
    return list(strings)
