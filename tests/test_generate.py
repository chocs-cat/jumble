"""Generation (§3.2 to §3.4) and the rule that randomness comes from `secrets`."""

import re
import secrets
from pathlib import Path

import pytest

from jumble import JumbleError, Settings, generate
from jumble.generate import CHARSETS, validate


def alphabet(settings: Settings) -> set[str]:
    return {c for _, chars in validate(settings) for c in chars}


@pytest.mark.parametrize(
    "settings",
    [
        Settings(),
        Settings(length=40, count=5, charsets=("digits",)),
        Settings(length=7, count=3, charsets=("emoji-faces", "box"), custom="xyz"),
        Settings(length=30, count=4, charsets=("lower", "symbols"), no_ambiguous=True),
    ],
)
def test_length_count_and_alphabet(settings: Settings) -> None:
    strings = generate(settings)
    assert len(strings) == settings.count
    allowed = alphabet(settings)
    for s in strings:
        assert len(s) == settings.length
        assert set(s) <= allowed


@pytest.mark.parametrize("length", [10, 62])
def test_no_repeat(length: int) -> None:
    for s in generate(Settings(length=length, count=20, no_repeat=True)):
        assert len(set(s)) == len(s) == length


def test_no_repeat_at_length_a_is_a_permutation() -> None:
    for s in generate(Settings(length=10, count=10, charsets=("digits",), no_repeat=True)):
        assert sorted(s) == list("0123456789")


EACH_CASES = [
    Settings(length=12, count=50, charsets=("lower", "digits", "dice"), custom="#", each=True),
    # length = k: every string is exactly one character from each set
    Settings(length=4, count=50, charsets=("lower", "digits", "dice"), custom="#", each=True),
    Settings(
        length=8, count=50, charsets=("upper", "chess"), custom="xy", each=True, no_repeat=True
    ),
    Settings(
        length=3, count=50, charsets=("upper", "chess"), custom="xy", each=True, no_repeat=True
    ),
]


@pytest.mark.parametrize("settings", EACH_CASES)
def test_each_takes_one_from_every_set(settings: Settings) -> None:
    sets = validate(settings)
    for s in generate(settings):
        assert len(s) == settings.length
        for name, chars in sets:
            assert set(s) & set(chars), f"{s!r} has nothing from {name}"
        if settings.no_repeat:
            assert len(set(s)) == len(s)


def test_each_with_no_repeat_at_length_a() -> None:
    settings = Settings(
        length=13, count=10, charsets=("digits",), custom="abc", each=True, no_repeat=True
    )
    for s in generate(settings):
        assert sorted(s) == sorted("0123456789abc")


def test_each_shuffles() -> None:
    # Without the shuffle the first character would always be from `lower`.
    first = {
        s[0]
        for s in generate(
            Settings(length=3, count=200, charsets=("lower", "digits"), custom="#", each=True)
        )
    }
    assert first & set("0123456789#")


def test_unique_has_no_duplicates() -> None:
    strings = generate(Settings(length=2, count=100, charsets=("digits",), unique=True))
    assert sorted(strings) == [f"{n:02}" for n in range(100)]


def test_impossible_unique_fails_before_any_draw(monkeypatch: pytest.MonkeyPatch) -> None:
    def no_draw(n: int) -> int:
        raise AssertionError("drew before validating")

    monkeypatch.setattr(secrets, "randbelow", no_draw)
    with pytest.raises(JumbleError) as e:
        generate(Settings(length=1, count=11, charsets=("digits",), unique=True))
    assert str(e.value) == "only 10 different strings are possible"


def test_unique_gives_up(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(secrets, "randbelow", lambda n: 0)
    with pytest.raises(JumbleError) as e:
        generate(Settings(count=2, unique=True))
    assert str(e.value) == "gave up after 100000 draws with 1 of 2 unique strings"


def test_unique_cap_grows_with_count(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(secrets, "randbelow", lambda n: 0)
    with pytest.raises(JumbleError) as e:
        generate(Settings(length=2, count=6000, charsets=tuple(CHARSETS), unique=True))
    assert str(e.value) == "gave up after 120000 draws with 1 of 6000 unique strings"


def test_draws_use_randbelow(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []

    def randbelow(n: int) -> int:
        calls.append(n)
        return 0

    monkeypatch.setattr(secrets, "randbelow", randbelow)
    assert generate(Settings(length=5, charsets=("digits",))) == ["00000"]
    assert calls == [10] * 5


def test_no_random_module_in_src() -> None:
    src = Path(__file__).parent.parent / "src"
    pattern = re.compile(r"^\s*(import\s+random\b|from\s+random\b)|SystemRandom", re.MULTILINE)
    files = sorted(src.rglob("*.py"))
    assert files
    for path in files:
        assert not pattern.search(path.read_text(encoding="utf-8")), path
