import io
import sys
from pathlib import Path

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


def test_help_lists_look_alikes_in_spec_order(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        main(["--help"])
    help_text = "".join(capsys.readouterr().out.split())
    # §3.1's order, typed out here so the test pins the spec, not the constant.
    assert "look-alikecharacters:0Ool1I|`'\";:.,-" in help_text


def test_output_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out = tmp_path / "out.txt"
    code, lines, err = run(["-s", "greek", "-n", "5", "-c", "3", "-o", str(out)], capsys)
    assert (code, lines, err) == (0, [], "")
    text = out.read_bytes().decode("utf-8")
    assert text.endswith("\n")
    written = text.split("\n")[:-1]
    assert len(written) == 3
    assert all(len(s) == 5 and set(s) <= set(CHARSETS["greek"]) for s in written)


def test_output_file_is_overwritten(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out = tmp_path / "out.txt"
    out.write_text("x" * 1000 + "\n")
    code, _, _ = run(["-n", "4", "-o", str(out)], capsys)
    assert code == 0
    data = out.read_bytes()
    assert len(data) == 5
    assert data.endswith(b"\n")


def test_output_dash_is_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    code, lines, err = run(["-n", "7", "-c", "2", "-o", "-"], capsys)
    assert (code, err) == (0, "")
    assert [len(line) for line in lines] == [7, 7]
    assert not Path("-").exists()


def test_stdout_is_utf8_whatever_its_encoding(monkeypatch: pytest.MonkeyPatch) -> None:
    raw = io.BytesIO()
    monkeypatch.setattr(sys, "stdout", io.TextIOWrapper(raw, encoding="ascii"))
    assert main(["-s", "emoji-faces", "-n", "8"]) == 0
    text = raw.getvalue().decode("utf-8")
    assert text.endswith("\n")
    line = text[:-1]
    assert len(line) == 8
    assert set(line) <= set(CHARSETS["emoji-faces"])


def test_failed_run_writes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Every draw is "00", so a unique run of two gives up (§3.4).
    monkeypatch.setattr("secrets.randbelow", lambda n: 0)
    missing, existing = tmp_path / "new.txt", tmp_path / "old.txt"
    existing.write_bytes(b"keep me\n")
    for out in (missing, existing):
        code, lines, err = run(["-s", "digits", "-c", "2", "-u", "-o", str(out)], capsys)
        assert (code, lines) == (2, [])
        assert err == "jumble: error: gave up after 100000 draws with 1 of 2 unique strings\n"
    assert not missing.exists()
    assert existing.read_bytes() == b"keep me\n"


def test_unwritable_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out = tmp_path / "missing" / "out.txt"
    code, lines, err = run(["-o", str(out)], capsys)
    assert (code, lines) == (1, [])
    assert err == f"jumble: error: can't write {out}: No such file or directory\n"
