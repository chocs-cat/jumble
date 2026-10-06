"""§6 validation, in order, and §3.5 strength."""

import math
from dataclasses import replace

import pytest

from jumble.generate import CHARSETS, JumbleError, Settings, strength, validate


def message(settings: Settings) -> str:
    with pytest.raises(JumbleError) as e:
        validate(settings)
    return str(e.value)


# One settings value per §6 row (all but "gave up", which is generation's),
# each failing that row alone, with its exact message, in table order.
ROWS: list[tuple[Settings, str]] = [
    (Settings(length=0), "length must be at least 1"),
    (Settings(count=0), "count must be at least 1"),
    (Settings(charsets=("lower", "emoji")), "unknown character set: 'emoji'"),
    (
        Settings(custom="á"),
        "custom characters can't include control or combining characters",
    ),
    (Settings(charsets=()), "choose at least one character set"),
    (
        Settings(charsets=("lower",), custom="abc"),
        "custom characters are all left out or already chosen",
    ),
    (
        Settings(length=3, charsets=("lower", "upper", "digits"), custom="!", each=True),
        "length must be at least 4 to take one character from each of 4 sets",
    ),
    (
        Settings(length=11, charsets=("digits",), no_repeat=True),
        "length can't be more than 10 without repeats",
    ),
    (
        Settings(length=2, count=101, charsets=("digits",), unique=True),
        "only 100 different strings are possible",
    ),
]


@pytest.mark.parametrize(("settings", "expected"), ROWS)
def test_each_row_fires_with_its_message(settings: Settings, expected: str) -> None:
    assert message(settings) == expected


def test_named_set_emptied_message() -> None:
    # The named sets are disjoint, so only no_ambiguous could empty one; none
    # empties today. The message is pinned through a set built to empty.
    with pytest.MonkeyPatch.context() as mp:
        mp.setitem(CHARSETS, "lower", "lo")
        assert message(Settings(charsets=("lower",), no_ambiguous=True)) == (
            "lower has no characters left"
        )


# For each adjacent pair of rows that can both fail, a value failing both gets
# the earlier row's message.
PAIRS: list[tuple[Settings, str]] = [
    (Settings(length=0, count=0), "length must be at least 1"),
    (Settings(count=0, charsets=("emoji",)), "count must be at least 1"),
    (Settings(length=0, charsets=("emoji",)), "length must be at least 1"),
    (Settings(charsets=("emoji",), custom="\x07"), "unknown character set: 'emoji'"),
    (
        Settings(charsets=(), custom="\x07"),
        "custom characters can't include control or combining characters",
    ),
    (
        Settings(charsets=("lower",), custom="a\x07"),
        "custom characters can't include control or combining characters",
    ),
    (
        Settings(length=1, charsets=("lower",), custom="a", each=True),
        "custom characters are all left out or already chosen",
    ),
    (
        Settings(
            length=1,
            charsets=("digits",),
            custom="!",
            each=True,
            no_repeat=True,
            count=99,
            unique=True,
        ),
        "length must be at least 2 to take one character from each of 2 sets",
    ),
    (
        Settings(length=11, count=11, charsets=("digits",), no_repeat=True, unique=True),
        "length can't be more than 10 without repeats",
    ),
]


@pytest.mark.parametrize(("settings", "expected"), PAIRS)
def test_earlier_row_wins(settings: Settings, expected: str) -> None:
    assert message(settings) == expected


def test_each_counts_custom_as_a_set() -> None:
    assert message(Settings(length=1, charsets=("digits",), custom="!", each=True)) == (
        "length must be at least 2 to take one character from each of 2 sets"
    )
    validate(Settings(length=2, charsets=("digits",), custom="!", each=True))


def test_no_repeat_allows_length_up_to_the_alphabet() -> None:
    validate(Settings(length=62, no_repeat=True))
    assert (
        message(Settings(length=63, no_repeat=True))
        == "length can't be more than 62 without repeats"
    )


@pytest.mark.parametrize(
    ("settings", "possible"),
    [
        (Settings(length=3, charsets=("digits",), unique=True), 1000),
        (Settings(length=3, charsets=("digits",), unique=True, no_repeat=True), 720),
    ],
)
def test_unique_allows_count_up_to_the_possible(settings: Settings, possible: int) -> None:
    validate(replace(settings, count=possible))
    assert message(replace(settings, count=possible + 1)) == (
        f"only {possible} different strings are possible"
    )


def test_validate_returns_the_sets() -> None:
    assert validate(Settings(charsets=("digits",), custom="x")) == [
        ("digits", "0123456789"),
        ("custom", "x"),
    ]


def test_strength_defaults() -> None:
    s = strength(Settings())
    assert s.alphabet_size == 62
    assert s.bits == pytest.approx(16 * math.log2(62))
    assert round(s.bits, 1) == 95.3
    assert s.is_bound is False


def test_strength_no_repeat() -> None:
    s = strength(Settings(no_repeat=True))
    expected = math.log2(math.factorial(62) // math.factorial(46))
    assert s.bits == pytest.approx(expected)
    assert s.bits < 16 * math.log2(62)


def test_strength_each_is_a_bound_with_the_same_bits() -> None:
    plain, each = strength(Settings()), strength(Settings(each=True))
    assert each.is_bound is True
    assert each.bits == plain.bits
    assert each.alphabet_size == plain.alphabet_size


def test_strength_of_a_long_string_does_not_overflow() -> None:
    assert strength(Settings(length=100_000)).bits == pytest.approx(100_000 * math.log2(62))


def test_strength_validates() -> None:
    with pytest.raises(JumbleError):
        strength(Settings(length=0))
