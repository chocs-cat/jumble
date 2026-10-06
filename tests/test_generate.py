import string

import pytest

from jumble import generate
from jumble.generate import AMBIGUOUS, alphabet


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
