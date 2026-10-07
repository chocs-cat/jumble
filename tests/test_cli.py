import errno
import io
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from jumble.cli import main, parser, settings_from
from jumble.generate import AMBIGUOUS, CHARSETS, Settings, settings_dict, validate


def run(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, list[str], str]:
    code = main(argv)
    out, err = capsys.readouterr()
    return code, out.splitlines(), err


def settings(*argv: str) -> Settings:
    return settings_from(parser().parse_args(argv), {})


def test_prints_count_strings(capsys: pytest.CaptureFixture[str]) -> None:
    code, lines, err = run(["-n", "10", "-c", "3", "-s", "upper"], capsys)
    assert (code, err) == (0, "")
    assert len(lines) == 3
    assert all(len(line) == 10 and line.isupper() for line in lines)


def test_defaults_when_nothing_chosen() -> None:
    assert settings() == Settings()


def test_long_options() -> None:
    # Every option of §4 by its long name.
    assert settings(
        "--length",
        "5",
        "--count",
        "2",
        "--charset",
        "digits,lower",
        "--custom",
        "!",
        "--no-ambiguous",
        "--each",
        "--no-repeat",
        "--unique",
    ) == Settings(5, 2, ("digits", "lower"), "!", True, True, True, True)
    args = parser().parse_args(["--output", "out.txt", "--json", "--strength", "--no-config"])
    assert (args.output, args.json, args.strength, args.no_config) == ("out.txt", True, True, True)


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
    ("value", "name"),
    # `custom` is not a set name: custom characters come only from --custom (§2.2).
    [("emoji", "emoji"), ("lower,", ""), ("lower,,digits", ""), ("custom", "custom")],
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


def test_closed_pipe_exits_quietly() -> None:
    # A real pipe: only a subprocess shows the exit-time flush (DEC-14).
    proc = subprocess.Popen(
        [sys.executable, "-m", "jumble", "-c", "200000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert proc.stdout is not None and proc.stderr is not None
    assert len(proc.stdout.readline()) == 17
    proc.stdout.close()
    err = proc.stderr.read()
    assert (proc.wait(timeout=30), err) == (1, b"")


def test_pipe_closed_before_writing_exits_quietly() -> None:
    # Output smaller than stdout's buffer stays in it after the failed flush,
    # and only fd 1 on the null device keeps the exit-time flush quiet (DEC-14).
    read_end, write_end = os.pipe()
    os.close(read_end)
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "jumble"],
            stdout=write_end,
            stderr=subprocess.PIPE,
            timeout=30,
        )
    finally:
        os.close(write_end)
    assert (proc.returncode, proc.stderr) == (1, b"")


class FullDisk(io.BytesIO):
    def write(self, data: Any) -> int:
        raise OSError(errno.ENOSPC, "No space left on device")


@pytest.mark.parametrize("argv", [[], ["-o", "-"]])
def test_unwritable_stdout(
    argv: list[str], monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "stdout", io.TextIOWrapper(FullDisk()))
    assert main(argv) == 1
    assert capsys.readouterr().err == "jumble: error: can't write stdout: No space left on device\n"


JSON_KEYS = ["strings", "alphabet_size", "strength_bits", "strength_is_bound", "settings"]


def run_json(argv: list[str], capsys: pytest.CaptureFixture[str]) -> dict[str, Any]:
    code = main(["--json", *argv])
    out, err = capsys.readouterr()
    assert (code, err) == (0, "")
    return json.loads(out)


def test_json_defaults(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--json"]) == 0
    out, err = capsys.readouterr()
    assert err == ""
    obj = json.loads(out)
    assert list(obj) == JSON_KEYS
    assert out == json.dumps(obj, indent=2, ensure_ascii=False) + "\n"
    assert len(obj["strings"]) == 1
    assert len(obj["strings"][0]) == 16
    assert (obj["alphabet_size"], obj["strength_bits"], obj["strength_is_bound"]) == (
        62,
        95.3,
        False,
    )
    # §1's defaults, in §1's order.
    assert list(obj["settings"].items()) == [
        ("length", 16),
        ("count", 1),
        ("charsets", ["lower", "upper", "digits"]),
        ("custom", ""),
        ("no_ambiguous", False),
        ("each", False),
        ("no_repeat", False),
        ("unique", False),
    ]


def test_json_charsets_once_in_canonical_order(capsys: pytest.CaptureFixture[str]) -> None:
    obj = run_json(["-s", "digits,lower,lower"], capsys)
    assert obj["settings"]["charsets"] == ["lower", "digits"]
    assert obj["alphabet_size"] == 36


def test_json_custom_alone(capsys: pytest.CaptureFixture[str]) -> None:
    obj = run_json(["--custom", "aab"], capsys)
    assert (obj["settings"]["charsets"], obj["settings"]["custom"]) == ([], "aab")
    assert obj["alphabet_size"] == 2


def test_json_settings_follow_the_options(capsys: pytest.CaptureFixture[str]) -> None:
    obj = run_json(["-n", "6", "-c", "3", "-s", "lower,digits", "-a", "-e", "-r", "-u"], capsys)
    assert obj["settings"] == {
        "length": 6,
        "count": 3,
        "charsets": ["lower", "digits"],
        "custom": "",
        "no_ambiguous": True,
        "each": True,
        "no_repeat": True,
        "unique": True,
    }
    assert obj["strength_is_bound"] is True
    assert len(set(obj["strings"])) == 3


def test_json_strength_is_rounded(capsys: pytest.CaptureFixture[str]) -> None:
    # log₂(10⁷) = 23.25…
    obj = run_json(["-s", "digits", "-n", "7"], capsys)
    assert obj["strength_bits"] == 23.3


def test_json_does_not_escape_emoji(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--json", "-s", "emoji-food", "-n", "3"]) == 0
    out = capsys.readouterr().out
    string = json.loads(out)["strings"][0]
    assert f'"{string}"' in out
    assert "\\u" not in out


def test_json_to_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out = tmp_path / "out.json"
    code, lines, err = run(["--json", "-o", str(out)], capsys)
    assert (code, lines, err) == (0, [], "")
    assert list(json.loads(out.read_bytes().decode("utf-8"))) == JSON_KEYS


def test_json_errors_are_plain(capsys: pytest.CaptureFixture[str]) -> None:
    code, lines, err = run(["--json", "-n", "0"], capsys)
    assert (code, lines, err) == (2, [], "jumble: error: length must be at least 1\n")


def test_strength_goes_to_stderr(capsys: pytest.CaptureFixture[str]) -> None:
    code, lines, err = run(["--strength", "-c", "3"], capsys)
    assert code == 0
    assert [len(line) for line in lines] == [16, 16, 16]
    assert err == "62 characters · 95.3 bits per string\n"


def test_strength_with_output_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out = tmp_path / "out.txt"
    code, lines, err = run(["--strength", "-e", "-o", str(out)], capsys)
    assert (code, lines) == (0, [])
    assert err == "62 characters · at most 95.3 bits per string\n"
    assert len(out.read_bytes()) == 17


def test_strength_not_printed_on_error(capsys: pytest.CaptureFixture[str]) -> None:
    code, lines, err = run(["--strength", "-n", "0"], capsys)
    assert (code, lines, err) == (2, [], "jumble: error: length must be at least 1\n")


@pytest.mark.parametrize(
    ("argv", "option"),
    [
        (["-o", "x", "tui"], "--output"),
        (["-o", "-", "tui"], "--output"),
        (["--json", "tui"], "--json"),
        (["--strength", "tui"], "--strength"),
        (["--strength", "--json", "tui"], "--json"),
        (["--strength", "--json", "-o", "x", "tui"], "--output"),
    ],
)
def test_misuse_with_tui(
    argv: list[str],
    option: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as exit_info:
        main(argv)
    assert exit_info.value.code == 2
    out, err = capsys.readouterr()
    assert out == ""
    assert err.startswith("usage:")
    assert err.endswith(f"jumble: error: {option} can't be used with tui\n")
    assert list(tmp_path.iterdir()) == []


class Launched:
    """Patches `JumbleApp.run` to record the app instead of running it."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from jumble.tui import JumbleApp

        self.apps: list[Any] = []
        monkeypatch.setattr(JumbleApp, "run", lambda app: self.apps.append(app))


@pytest.mark.parametrize(
    ("argv", "start"),
    [
        (["-n", "32", "-s", "digits", "tui"], Settings(length=32, charsets=("digits",))),
        (["tui"], Settings()),
        (["--custom", "abc", "tui"], Settings(charsets=(), custom="abc")),
        # Bad values the controls can hold start the TUI (§7.5, DEC-16).
        (["-n", "0", "tui"], Settings(length=0)),
    ],
)
def test_tui_starts_from_the_options(
    argv: list[str], start: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    launched = Launched(monkeypatch)
    assert main(argv) == 0
    assert [app.initial for app in launched.apps] == [start]


@pytest.mark.parametrize(
    ("argv", "name"),
    [
        (["-s", "foo", "tui"], "foo"),
        (["-s", "lower,", "tui"], ""),
        (["-s", "digits", "-s", "bar,baz", "tui"], "bar"),
    ],
)
def test_tui_rejects_unknown_sets(
    argv: list[str],
    name: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    launched = Launched(monkeypatch)
    code, lines, err = run(argv, capsys)
    assert (code, lines) == (2, [])
    assert err == f"jumble: error: unknown character set: '{name}'\n"
    assert launched.apps == []


def test_tui_help_says_what_sets_its_start(capsys: pytest.CaptureFixture[str]) -> None:
    # The effective settings: the file, then the options before tui (§7.5).
    with pytest.raises(SystemExit):
        main(["tui", "--help"])
    out = " ".join(capsys.readouterr().out.split())
    assert "It starts from the settings file, and options given before tui override it" in out
    assert "jumble -n 32 -s digits tui" in out
    with pytest.raises(SystemExit):
        main(["--help"])
    out = " ".join(capsys.readouterr().out.split())
    assert "starting from the settings file and the options before tui" in out


# The settings file (§5): `config_file` is $JUMBLE_CONFIG, missing until written.


def test_file_reaches_the_settings(config_file: Path, capsys: pytest.CaptureFixture[str]) -> None:
    config_file.write_text(
        'length = 6\ncount = 3\ncharsets = ["digits", "lower"]\ncustom = "XY"\n'
        "no_ambiguous = true\neach = true\nno_repeat = true\nunique = true\n"
    )
    obj = run_json([], capsys)
    assert obj["settings"] == {
        "length": 6,
        "count": 3,
        "charsets": ["lower", "digits"],
        "custom": "XY",
        "no_ambiguous": True,
        "each": True,
        "no_repeat": True,
        "unique": True,
    }
    assert len(obj["strings"]) == 3


def test_an_option_at_its_default_beats_the_file(
    config_file: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config_file.write_text("length = 32\ncount = 4\n")
    settings = run_json(["-n", "16", "-c", "1"], capsys)["settings"]
    assert (settings["length"], settings["count"]) == (16, 1)


def test_file_keys_the_command_line_leaves_alone_stay(
    config_file: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config_file.write_text("length = 32\neach = true\n")
    settings = run_json(["-c", "2", "-u"], capsys)["settings"]
    assert (settings["length"], settings["count"]) == (32, 2)
    assert (settings["each"], settings["unique"]) == (True, True)


def test_charset_replaces_the_files_characters(
    config_file: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config_file.write_text('charsets = ["greek"]\ncustom = "XY"\n')
    settings = run_json(["-s", "digits"], capsys)["settings"]
    assert (settings["charsets"], settings["custom"]) == (["digits"], "")


def test_empty_custom_replaces_the_files_characters(
    config_file: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config_file.write_text('charsets = ["greek"]\ncustom = "XY"\n')
    settings = run_json(["--custom", ""], capsys)["settings"]
    assert (settings["charsets"], settings["custom"]) == (["lower", "upper", "digits"], "")


def test_file_custom_alone_is_the_only_characters(
    config_file: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config_file.write_text('custom = "abc"\n')
    code, lines, _ = run(["-n", "50", "-c", "5"], capsys)
    assert code == 0
    assert all(set(line) <= set("abc") for line in lines)


def test_file_with_no_characters_gets_the_defaults(
    config_file: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config_file.write_text('charsets = []\ncustom = ""\n')
    assert run_json([], capsys)["settings"]["charsets"] == ["lower", "upper", "digits"]


def test_file_each_with_a_short_command_line_length(
    config_file: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config_file.write_text("each = true\n")
    code, lines, err = run(["-n", "2", "-s", "lower,upper,digits"], capsys)
    assert (code, lines) == (2, [])
    assert err == (
        "jumble: error: length must be at least 3 to take one character from each of 3 sets\n"
    )


def test_no_config_ignores_a_broken_file(
    config_file: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config_file.write_text("length = 0\n")
    code = main(["--no-config", "--json"])
    out, err = capsys.readouterr()
    assert (code, err) == (0, "")
    assert json.loads(out)["settings"] == settings_dict(Settings())


@pytest.mark.parametrize("argv", [[], ["-n", "8"]])
def test_a_file_error_stops_the_run(
    argv: list[str], config_file: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config_file.write_text("length = 0\n")
    code = main(argv)
    out, err = capsys.readouterr()
    assert (code, out) == (2, "")
    assert err == f"jumble: error: {config_file}: length: length must be at least 1\n"


def test_a_file_error_writes_no_output_file(
    config_file: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config_file.write_text("colour = 1\n")
    out = tmp_path / "out.txt"
    out.write_text("keep\n")
    assert main(["-o", str(out)]) == 2
    assert out.read_text() == "keep\n"


def test_an_unreadable_file(config_file: Path, capsys: pytest.CaptureFixture[str]) -> None:
    config_file.mkdir()
    code = main([])
    out, err = capsys.readouterr()
    assert (code, out) == (2, "")
    assert err == f"jumble: error: can't read {config_file}: Is a directory\n"


def test_the_installed_command_reads_the_file(config_file: Path) -> None:
    # The fixture's $JUMBLE_CONFIG reaches subprocesses too.
    config_file.write_text("length = 0\n")
    proc = subprocess.run(
        [sys.executable, "-m", "jumble"], capture_output=True, text=True, check=False
    )
    assert (proc.returncode, proc.stdout) == (2, "")
    assert proc.stderr == f"jumble: error: {config_file}: length: length must be at least 1\n"


def test_help_names_no_config(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        main(["--help"])
    assert "--no-config" in capsys.readouterr().out


# The TUI starts from the settings file too (§7.4, §7.5).


@pytest.mark.parametrize(
    ("argv", "length"),
    [(["tui"], 32), (["-n", "8", "tui"], 8), (["--no-config", "tui"], 16)],
)
def test_tui_starts_from_the_file(
    argv: list[str], length: int, config_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_file.write_text("length = 32\n")
    launched = Launched(monkeypatch)
    assert main(argv) == 0
    assert [(app.initial.length, app.file_error) for app in launched.apps] == [(length, None)]


def test_a_file_error_starts_the_tui_without_the_file(
    config_file: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    config_file.write_text("count = 5\nlength = 0\n")
    launched = Launched(monkeypatch)
    assert main(["-n", "8", "tui"]) == 0
    assert capsys.readouterr() == ("", "")
    [app] = launched.apps
    assert app.initial == Settings(length=8)
    assert app.file_error == f"{config_file}: length: length must be at least 1"


def test_an_unknown_set_still_stops_the_tui_with_a_broken_file(
    config_file: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    config_file.write_text("length = 0\n")
    launched = Launched(monkeypatch)
    code, _, err = run(["-s", "foo", "tui"], capsys)
    assert (code, err) == (2, "jumble: error: unknown character set: 'foo'\n")
    assert launched.apps == []


@pytest.mark.parametrize(
    ("line", "message"),
    [
        ("colour = 1", "colour: unknown setting"),
        ("length = true", "length: must be an integer"),
        ('charsets = ["foo"]', "charsets: unknown character set: 'foo'"),
    ],
)
def test_file_errors_name_the_file_and_key(
    line: str, message: str, config_file: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config_file.write_text(line + "\n")
    code = main(["-s", "digits"])
    out, err = capsys.readouterr()
    assert (code, out) == (2, "")
    assert err == f"jumble: error: {config_file}: {message}\n"
