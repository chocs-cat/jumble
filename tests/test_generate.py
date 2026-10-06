import string
import unicodedata

import pytest

from jumble import generate
from jumble.generate import AMBIGUOUS, CHARSETS, JumbleError, Settings, alphabet, chosen_sets


def test_length_and_charset() -> None:
    s = generate(40, ["digits"])
    assert len(s) == 40
    assert set(s) <= set(string.digits)


def test_exclude_ambiguous() -> None:
    assert not set(alphabet(["lower", "upper", "digits"], exclude_ambiguous=True)) & AMBIGUOUS


@pytest.mark.parametrize(
    ("length", "charsets"),
    [(0, ["lower"]), (8, []), (8, ["emoji"])],
)
def test_rejects_bad_input(length: int, charsets: list[str]) -> None:
    with pytest.raises(ValueError):
        generate(length, charsets)


# --- §2.1 named sets, §2.3 custom characters, §2.4 the alphabet ---


def cps(*ranges: tuple[int, int], without: tuple[int, ...] = ()) -> str:
    """The code points of the inclusive `ranges`, less `without`, in order."""
    return "".join(chr(c) for lo, hi in ranges for c in range(lo, hi + 1) if c not in without)


# Name, expected characters, and size, transcribed from spec §2.1 in its order.
SPEC_SETS: list[tuple[str, str, int]] = [
    ("lower", cps((0x61, 0x7A)), 26),
    ("upper", cps((0x41, 0x5A)), 26),
    ("digits", cps((0x30, 0x39)), 10),
    ("symbols", "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~", 32),
    ("space", " ", 1),
    ("chess", cps((0x2654, 0x265F)), 12),
    (
        "cards",
        cps(
            (0x1F0A1, 0x1F0AE),
            (0x1F0B1, 0x1F0BE),
            (0x1F0C1, 0x1F0CE),
            (0x1F0D1, 0x1F0DE),
            without=(0x1F0AC, 0x1F0BC, 0x1F0CC, 0x1F0DC),
        ),
        52,
    ),
    ("dice", cps((0x2680, 0x2685)), 6),
    ("emoji-faces", cps((0x1F600, 0x1F64F)), 80),
    ("emoji-animals", cps((0x1F400, 0x1F43E)), 63),
    ("emoji-food", cps((0x1F345, 0x1F37B)), 55),
    ("greek", cps((0x0391, 0x03A9), (0x03B1, 0x03C9), without=(0x03A2, 0x03C2)), 48),
    ("cyrillic", cps((0x0410, 0x044F)), 64),
    ("latin-accented", cps((0x00C0, 0x00FF), without=(0x00D7, 0x00F7)), 62),
    ("arrows", cps((0x2190, 0x2199)), 10),
    ("math", "±×÷∞≠≈≤≥√∑∏∫∂∆∇∈∉∩∪⊂⊃∀∃¬∧∨", 26),
    ("currency", "¢£¥€₹₽₩₪₺₿₫₱", 12),
    ("box", cps((0x2500, 0x259F)), 160),
]


def test_charsets_are_the_spec_sets_in_canonical_order() -> None:
    assert list(CHARSETS) == [name for name, _, _ in SPEC_SETS]


@pytest.mark.parametrize(("name", "expected", "size"), SPEC_SETS)
def test_named_set_matches_spec(name: str, expected: str, size: int) -> None:
    assert CHARSETS[name] == expected
    assert len(CHARSETS[name]) == size
    for c in CHARSETS[name]:
        assert unicodedata.category(c)[0] not in "CM", f"{name}: U+{ord(c):04X}"


def test_named_sets_are_disjoint() -> None:
    seen: set[str] = set()
    for chars in CHARSETS.values():
        assert not seen & set(chars)
        seen.update(chars)


def test_ambiguous_is_the_spec_list() -> None:
    assert (
        set(["0", "O", "o", "l", "1", "I", "|", "`", "'", '"', ";", ":", ".", ",", "-"])
        == AMBIGUOUS
    )
    assert len(AMBIGUOUS) == 15


def test_settings_defaults_are_spec_1() -> None:
    s = Settings()
    assert (s.length, s.count, s.charsets, s.custom) == (16, 1, ("lower", "upper", "digits"), "")
    assert not (s.no_ambiguous or s.each or s.no_repeat or s.unique)
    assert [f for f in Settings.__dataclass_fields__] == [
        "length",
        "count",
        "charsets",
        "custom",
        "no_ambiguous",
        "each",
        "no_repeat",
        "unique",
    ]


def test_jumble_error_is_a_value_error() -> None:
    assert issubclass(JumbleError, ValueError)


def test_sets_come_in_canonical_order_with_custom_last() -> None:
    sets = chosen_sets(Settings(charsets=("digits", "chess", "lower", "digits"), custom="!x"))
    assert [name for name, _ in sets] == ["lower", "digits", "chess", "custom"]


def test_custom_dedupe_keeps_first_position() -> None:
    assert chosen_sets(Settings(charsets=(), custom="!x!yx"))[-1] == ("custom", "!xy")


def test_overlaps_stay_in_the_earlier_set() -> None:
    sets = dict(chosen_sets(Settings(charsets=("lower",), custom="abcX")))
    assert sets["lower"] == CHARSETS["lower"]
    assert sets["custom"] == "X"


def test_no_ambiguous_applies_to_every_set_including_custom() -> None:
    sets = dict(
        chosen_sets(
            Settings(charsets=("lower", "digits", "symbols"), custom="O!Z", no_ambiguous=True)
        )
    )
    assert sets["lower"] == CHARSETS["lower"].replace("l", "").replace("o", "")
    assert sets["digits"] == "23456789"
    assert not set(sets["symbols"]) & AMBIGUOUS
    assert sets["custom"] == "Z"  # O is a look-alike; ! is already in symbols


@pytest.mark.parametrize(
    "char", ["\x07", "\u200b", "\u0301", "\ue000", "\ud800", "\U0010fffe", "\U000e0001"]
)
def test_custom_rejects_control_and_combining(char: str) -> None:
    with pytest.raises(JumbleError) as e:
        chosen_sets(Settings(custom="ab" + char))
    assert str(e.value) == "custom characters can't include control or combining characters"


def test_empty_custom_is_not_a_set() -> None:
    assert [name for name, _ in chosen_sets(Settings())] == ["lower", "upper", "digits"]
