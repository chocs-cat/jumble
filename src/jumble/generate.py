"""Generate random strings from named character sets."""

import secrets
import string
from collections.abc import Iterable

CHARSETS: dict[str, str] = {
    "lower": string.ascii_lowercase,
    "upper": string.ascii_uppercase,
    "digits": string.digits,
    "symbols": "!#$%&()*+,-./:;<=>?@[]^_{|}~",
}

# Characters that are easy to misread for one another.
AMBIGUOUS = set("Il1O0o")


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
