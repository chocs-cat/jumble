import pytest

from jumble.cli import main, parser, settings_from
from jumble.generate import AMBIGUOUS, CHARSETS, Settings, validate


def run(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, list[str], str]:
    code = main(argv)
    out, err = capsys.readouterr()
    return code, out.splitlines(), err


def settings(*argv: str) -> Settings:
    return settings_from(parser().parse_args(argv))


def test_prints_count_strings(capsys: pytest.CaptureFixture[str]) -> None:
    code, lines, err = run(["-n", "10", "-c", "3", "-s", "upper"], capsys)
    assert (code, err) == (0, "")
    assert len(lines) == 3
    assert all(len(line) == 10 and line.isupper() for line in lines)


def test_defaults_when_nothing_chosen() -> None:
    assert settings() == Settings()


def test_commas_and_repeats_choose_the_same_sets() -> None:
    a, b = settings("-s", "lower,digits"), settings("-s", "lower", "-s", "digits")
    assert validate(a) == validate(b)
    assert [name for name, _ in validate(a)] == ["lower", "digits"]


def test_custom_alone_replaces_the_defaults(capsys: pytest.CaptureFixture[str]) -> None:
    code, lines, _ = run(["--custom", "abc", "-n", "50", "-c", "5"], capsys)
    assert code == 0
    assert all(set(line) <= set("abc") for line in lines)


def test_custom_already_chosen(capsys: pytest.CaptureFixture[str]) -> None:
    code, lines, err = run(["--custom", "abc", "-s", "lower"], capsys)
    assert (code, lines) == (2, [])
    assert err == "jumble: error: custom characters are all left out or already chosen\n"


@pytest.mark.parametrize(
    ("value", "name"), [("emoji", "emoji"), ("lower,", ""), ("lower,,digits", "")]
)
def test_unknown_or_empty_set(value: str, name: str, capsys: pytest.CaptureFixture[str]) -> None:
    code, lines, err = run(["-s", value], capsys)
    assert (code, lines) == (2, [])
    assert err == f"jumble: error: unknown character set: '{name}'\n"


def test_bad_length(capsys: pytest.CaptureFixture[str]) -> None:
    code, lines, err = run(["-n", "0"], capsys)
    assert (code, lines, err) == (2, [], "jumble: error: length must be at least 1\n")


def test_each(capsys: pytest.CaptureFixture[str]) -> None:
    code, lines, _ = run(["-e", "-n", "2", "-c", "50", "-s", "lower,digits"], capsys)
    assert code == 0
    for line in lines:
        assert sorted(c.isdigit() for c in line) == [False, True]


def test_no_repeat(capsys: pytest.CaptureFixture[str]) -> None:
    code, lines, _ = run(["-r", "-n", "10", "-c", "20", "-s", "digits"], capsys)
    assert code == 0
    assert all(sorted(line) == list("0123456789") for line in lines)


def test_unique(capsys: pytest.CaptureFixture[str]) -> None:
    code, lines, _ = run(["-u", "-n", "1", "-c", "10", "-s", "digits"], capsys)
    assert code == 0
    assert sorted(lines) == list("0123456789")


def test_no_ambiguous(capsys: pytest.CaptureFixture[str]) -> None:
    code, lines, _ = run(["-a", "-n", "200", "-s", "digits"], capsys)
    assert code == 0
    assert set(lines[0]) <= set("23456789")


def test_help_lists_sets_and_look_alikes(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        main(["--help"])
    # argparse wraps lines, even inside a name like emoji-food.
    help_text = "".join(capsys.readouterr().out.split())
    for name in CHARSETS:
        assert name in help_text
    for option in ("--custom", "--each", "--no-repeat", "--unique"):
        assert option in help_text
    assert all(c in help_text.partition("--no-ambiguous")[2] for c in AMBIGUOUS)
