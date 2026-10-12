import errno
import json
import string
import time
from collections.abc import Iterator
from importlib.metadata import version
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest
from textual import events
from textual.app import App
from textual.containers import VerticalScroll
from textual.geometry import Region
from textual.pilot import Pilot
from textual.widget import Widget
from textual.widgets import Button, Checkbox, Footer, Input, OptionList, SelectionList, Static

from jumble import tui
from jumble.cli import main, parser, settings_from
from jumble.config import file_settings, load
from jumble.generate import CHARSETS, JumbleError, Settings, settings_dict, strength, strength_line
from jumble.tui import HelpScreen, JumbleApp, SettingsScreen, characters, read_controls


def results(app: JumbleApp) -> list[str]:
    pane = app.query_one("#results", OptionList)
    return [str(pane.get_option_at_index(i).prompt) for i in range(pane.option_count)]


def banner(app: JumbleApp) -> str | None:
    """The error banner's text while it is shown, else None."""
    error = app.query_one("#error", Static)
    return str(error.content) if error.display else None


async def set_value(pilot: Pilot[None], selector: str, value: str) -> None:
    pilot.app.query_one(selector, Input).value = value
    await pilot.pause()


async def check(pilot: Pilot[None], selector: str) -> None:
    pilot.app.query_one(selector, Checkbox).value = True
    await pilot.pause()


async def choose_only(pilot: Pilot[None], *names: str) -> None:
    sets = pilot.app.query_one("#charsets", SelectionList)
    sets.deselect_all()
    for name in names:
        sets.select(name)
    await pilot.pause()


VALID = "62 characters · 95.3 bits per string"


async def test_header_at_start() -> None:
    app = JumbleApp()
    async with app.run_test():
        assert app.title == f"jumble {version('jumble-cli')}"
        assert app.sub_title == VALID
        assert banner(app) is None
        assert len(results(app)) == 1


async def test_each_makes_the_subtitle_a_bound() -> None:
    app = JumbleApp()
    async with app.run_test() as pilot:
        await check(pilot, "#each")
        assert app.sub_title == "62 characters · at most 95.3 bits per string"


async def test_bad_length_shows_the_banner_and_blocks_g() -> None:
    app = JumbleApp()
    async with app.run_test() as pilot:
        before = results(app)
        for value in ("0", "", "-"):
            await set_value(pilot, "#length", value)
            assert banner(app) == "length must be at least 1"
            assert app.sub_title == ""
            await pilot.press("g")
            await pilot.pause()
            assert results(app) == before
        await set_value(pilot, "#length", "16")
        assert banner(app) is None
        assert app.sub_title == VALID


async def test_bad_count() -> None:
    app = JumbleApp()
    async with app.run_test() as pilot:
        await set_value(pilot, "#count", "")
        assert banner(app) == "count must be at least 1"


async def test_no_sets_is_an_error_not_the_defaults() -> None:
    app = JumbleApp()
    async with app.run_test() as pilot:
        await choose_only(pilot)
        assert banner(app) == "choose at least one character set"
        assert app.sub_title == ""
        await set_value(pilot, "#custom", "xyz")
        assert banner(app) is None
        assert app.sub_title == "3 characters · 25.4 bits per string"


async def test_custom_already_chosen() -> None:
    app = JumbleApp()
    async with app.run_test() as pilot:
        await choose_only(pilot, "lower")
        await set_value(pilot, "#custom", "abc")
        assert banner(app) == "custom characters are all left out or already chosen"
        assert app.sub_title == ""
        await set_value(pilot, "#custom", "")
        assert banner(app) is None
        assert app.sub_title == "26 characters · 75.2 bits per string"


async def test_options_reach_validation() -> None:
    app = JumbleApp()
    async with app.run_test() as pilot:
        await choose_only(pilot, "digits")
        await check(pilot, "#no-repeat")
        assert banner(app) == "length can't be more than 10 without repeats"
        await check(pilot, "#no-ambiguous")
        assert banner(app) == "length can't be more than 8 without repeats"
        await set_value(pilot, "#length", "2")
        await set_value(pilot, "#count", "57")
        await check(pilot, "#unique")
        assert banner(app) == "only 56 different strings are possible"


async def test_g_uses_the_controls() -> None:
    app = JumbleApp()
    async with app.run_test() as pilot:
        await set_value(pilot, "#length", "24")
        await set_value(pilot, "#count", "5")
        await choose_only(pilot, "digits")
        await pilot.press("g")
        await pilot.pause()
        rows = results(app)
        assert len(rows) == 5
        assert all(len(row) == 24 and row.isdigit() for row in rows)


async def test_changing_a_control_keeps_the_results() -> None:
    app = JumbleApp()
    async with app.run_test() as pilot:
        before = results(app)
        await set_value(pilot, "#length", "30")
        assert results(app) == before


async def test_markup_characters_show_as_themselves() -> None:
    app = JumbleApp()
    async with app.run_test() as pilot:
        await choose_only(pilot)
        await set_value(pilot, "#custom", "[]")
        await set_value(pilot, "#length", "40")
        await pilot.press("g")
        await pilot.pause()
        assert set(results(app)[0]) == {"[", "]"}


async def test_set_list_is_canonical() -> None:
    app = JumbleApp()
    async with app.run_test():
        sets = app.query_one("#charsets", SelectionList)
        names = [sets.get_option_at_index(i).value for i in range(sets.option_count)]
        assert names == list(CHARSETS)
        assert sets.selected == ["lower", "upper", "digits"]


async def test_option_checkboxes_start_off() -> None:
    app = JumbleApp()
    async with app.run_test():
        for wid in ("no-ambiguous", "each", "no-repeat", "unique"):
            assert app.query_one(f"#{wid}", Checkbox).value is False
        assert app.query_one("#length", Input).value == "16"
        assert app.query_one("#count", Input).value == "1"


class Recorder:
    """Records what the app copies and the toasts it shows."""

    def __init__(self, app: JumbleApp, monkeypatch: pytest.MonkeyPatch) -> None:
        self.copied: list[str] = []
        self.toasts: list[str] = []
        self.severities: list[str] = []
        monkeypatch.setattr(app, "copy_to_clipboard", self.copied.append)
        monkeypatch.setattr(app, "notify", self.notify)

    def notify(self, message: str, *, severity: str = "information", **_: object) -> None:
        self.toasts.append(message)
        self.severities.append(severity)


async def test_more_than_1000_strings(monkeypatch: pytest.MonkeyPatch) -> None:
    app = JumbleApp()
    async with app.run_test() as pilot:
        record = Recorder(app, monkeypatch)
        await set_value(pilot, "#count", "1500")
        await pilot.press("g")
        await pilot.pause()
        rows = results(app)
        assert len(rows) == 1001
        assert rows[-1] == "… and 500 more (s saves all)"
        assert rows[:1000] == app.strings[:1000]
        pane = app.query_one("#results", OptionList)
        assert pane.highlighted == 0
        await pilot.press("end")
        assert pane.highlighted == 999
        await pilot.press("down")
        assert pane.highlighted != 1000
        await pilot.press("end")
        await pilot.press("c")
        assert record.copied == [app.strings[999]]
        await pilot.press("a")
        assert record.copied[-1].split("\n") == app.strings
        assert len(app.strings) == 1500
        assert record.toasts == ["Copied", "Copied 1500 strings"]


async def test_c_copies_the_highlighted_string(monkeypatch: pytest.MonkeyPatch) -> None:
    app = JumbleApp()
    async with app.run_test() as pilot:
        record = Recorder(app, monkeypatch)
        await set_value(pilot, "#count", "3")
        await pilot.press("g", "down", "c")
        assert record.copied == [app.strings[1]]
        assert record.toasts == ["Copied"]


async def test_jumble_moves_the_cursor_to_the_top() -> None:
    app = JumbleApp()
    async with app.run_test() as pilot:
        await set_value(pilot, "#count", "3")
        await pilot.press("g", "down", "down", "g")
        assert app.query_one("#results", OptionList).highlighted == 0


async def test_copy_one_string(monkeypatch: pytest.MonkeyPatch) -> None:
    app = JumbleApp()
    async with app.run_test() as pilot:
        record = Recorder(app, monkeypatch)
        await pilot.press("a")
        assert record.copied == app.strings
        assert record.toasts == ["Copied 1 string"]


async def test_copying_while_invalid_uses_the_last_result(monkeypatch: pytest.MonkeyPatch) -> None:
    app = JumbleApp()
    async with app.run_test() as pilot:
        record = Recorder(app, monkeypatch)
        await set_value(pilot, "#count", "2")
        await pilot.press("g")
        last = list(app.strings)
        await set_value(pilot, "#length", "0")
        app.query_one("#results", OptionList).focus()
        await pilot.press("g", "a", "c")
        assert record.copied == ["\n".join(last), last[0]]


async def test_keys_before_any_strings_do_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    app = JumbleApp()
    # Invalid from the start, so the start-up jumble makes nothing (§7.2).
    monkeypatch.setattr(app, "check", lambda: setattr(app, "valid", False))
    async with app.run_test() as pilot:
        record = Recorder(app, monkeypatch)
        await pilot.press("c", "a")
        assert (record.copied, record.toasts) == ([], [])
        assert results(app) == []


async def test_q_quits() -> None:
    app = JumbleApp()
    async with app.run_test() as pilot:
        await pilot.press("q")
        await pilot.pause()
        assert not app.is_running


async def test_the_main_screen_has_no_buttons() -> None:
    # Keys in the footer, not a Jumble button (§7.2, DEC-12).
    app = JumbleApp()
    async with app.run_test():
        assert not app.screen.query(Button)


async def test_focus_starts_on_the_results() -> None:
    app = JumbleApp()
    async with app.run_test():
        assert app.focused is app.query_one("#results", OptionList)


async def test_enter_in_an_input_jumbles_and_leaves_it() -> None:
    app = JumbleApp()
    async with app.run_test() as pilot:
        before = results(app)
        app.query_one("#length", Input).focus()
        await pilot.press("enter")
        await pilot.pause()
        assert results(app) != before
        assert app.focused is app.query_one("#results", OptionList)


async def test_enter_while_invalid_only_leaves_the_input() -> None:
    app = JumbleApp()
    async with app.run_test() as pilot:
        before = results(app)
        await set_value(pilot, "#length", "0")
        app.query_one("#length", Input).focus()
        await pilot.press("enter")
        await pilot.pause()
        assert results(app) == before
        assert app.focused is app.query_one("#results", OptionList)


async def test_escape_leaves_an_input_without_jumbling() -> None:
    app = JumbleApp()
    async with app.run_test() as pilot:
        before = results(app)
        app.query_one("#custom", Input).focus()
        await pilot.press("escape")
        await pilot.pause()
        assert results(app) == before
        assert app.focused is app.query_one("#results", OptionList)


async def test_footer_keys() -> None:
    app = JumbleApp()
    async with app.run_test():
        # Results-pane focus, as at start: the screen's bindings, not an input's.
        bindings = app.screen.active_bindings.values()
        shown = [(a.binding.key, a.binding.description) for a in bindings if a.binding.show]
        assert shown == [
            ("g", "Jumble"),
            ("c", "Copy"),
            ("a", "Copy all"),
            ("s", "Save"),
            ("d", "Save defaults"),
            ("comma", "Settings"),
            ("question_mark", "Help"),
            ("q", "Quit"),
        ]
        comma = next(a.binding for a in bindings if a.binding.key == "comma")
        assert app.get_key_display(comma) == ","


GAVE_UP = "gave up after 100000 draws with 9 of 10 unique strings"


def give_up(_settings: object) -> list[str]:
    raise JumbleError(GAVE_UP)


async def test_a_give_up_is_a_toast(monkeypatch: pytest.MonkeyPatch) -> None:
    app = JumbleApp()
    async with app.run_test() as pilot:
        record = Recorder(app, monkeypatch)
        await set_value(pilot, "#count", "3")
        await pilot.press("g", "down")
        before, strings = results(app), list(app.strings)
        monkeypatch.setattr(tui, "generate", give_up)
        await pilot.press("g")
        await pilot.pause()
        assert app.is_running
        assert results(app) == before
        assert app.strings == strings
        assert app.query_one("#results", OptionList).highlighted == 1
        assert banner(app) is None
        assert (record.toasts, record.severities) == ([GAVE_UP], ["error"])


async def test_a_give_up_through_enter_is_a_toast(monkeypatch: pytest.MonkeyPatch) -> None:
    app = JumbleApp()
    async with app.run_test() as pilot:
        record = Recorder(app, monkeypatch)
        before = results(app)
        monkeypatch.setattr(tui, "generate", give_up)
        app.query_one("#length", Input).focus()
        await pilot.press("enter")
        await pilot.pause()
        assert app.is_running
        assert results(app) == before
        assert app.query_one("#results", OptionList).highlighted == 0
        assert banner(app) is None
        assert (record.toasts, record.severities) == ([GAVE_UP], ["error"])


def selected(app: JumbleApp) -> list[str]:
    return list(app.query_one("#charsets", SelectionList).selected)


async def test_starting_values() -> None:
    app = JumbleApp(Settings(length=32, charsets=("digits",)))
    async with app.run_test():
        assert app.query_one("#length", Input).value == "32"
        assert selected(app) == ["digits"]
        assert app.sub_title == "10 characters · 106.3 bits per string"
        assert banner(app) is None
        rows = results(app)
        assert len(rows) == 1
        assert len(rows[0]) == 32 and rows[0].isdigit()


async def test_every_option_and_custom_reach_their_control() -> None:
    start = Settings(
        count=3,
        charsets=("lower", "greek"),
        custom="xyz!",
        no_ambiguous=True,
        each=True,
        no_repeat=True,
        unique=True,
    )
    app = JumbleApp(start)
    async with app.run_test():
        assert app.query_one("#count", Input).value == "3"
        assert app.query_one("#custom", Input).value == "xyz!"
        assert selected(app) == ["lower", "greek"]
        for wid in ("no-ambiguous", "each", "no-repeat", "unique"):
            assert app.query_one(f"#{wid}", Checkbox).value is True
        assert app.settings() == start
        assert len(app.strings) == 3


async def test_custom_alone_starts_with_no_sets() -> None:
    app = JumbleApp(Settings(charsets=(), custom="ab"))
    async with app.run_test():
        assert selected(app) == []
        assert app.sub_title == "2 characters · 16.0 bits per string"
        assert set(results(app)[0]) <= {"a", "b"}


async def test_an_invalid_start_shows_the_banner_and_no_strings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = JumbleApp(Settings(length=0))
    async with app.run_test() as pilot:
        record = Recorder(app, monkeypatch)
        assert banner(app) == "length must be at least 1"
        assert app.sub_title == ""
        assert results(app) == []
        assert app.strings == []
        await pilot.press("g", "c", "a")
        assert (record.copied, record.toasts) == ([], [])
        assert results(app) == []


async def test_a_file_error_is_a_toast(monkeypatch: pytest.MonkeyPatch) -> None:
    message = "X: length: length must be at least 1"
    app = JumbleApp(Settings(), file_error=message)
    record = Recorder(app, monkeypatch)  # before mount, which shows the toast
    async with app.run_test():
        assert (record.toasts, record.severities) == ([message], ["error"])
        assert banner(app) is None
        assert len(results(app)) == 1


async def test_no_file_error_no_toast(monkeypatch: pytest.MonkeyPatch) -> None:
    app = JumbleApp(Settings())
    record = Recorder(app, monkeypatch)
    async with app.run_test():
        assert record.toasts == []


async def test_a_files_each_with_a_short_length_starts_with_the_banner() -> None:
    # `each` from a file and too short a length: the banner, not an error (DEC-16).
    app = JumbleApp(Settings(length=2, each=True))
    async with app.run_test():
        assert banner(app) == (
            "length must be at least 3 to take one character from each of 3 sets"
        )
        assert results(app) == []


NAME = "jumble-1760000000-1500.txt"


@pytest.fixture
def here(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """An empty working directory, and a clock at 1760000000.7 for a known name (§7.3)."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(time, "time", lambda: 1760000000.7)
    return tmp_path


def lines(strings: list[str]) -> bytes:
    return "".join(f"{s}\n" for s in strings).encode()


async def test_s_saves_every_string(here: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    app = JumbleApp(Settings(count=1500))
    async with app.run_test() as pilot:
        record = Recorder(app, monkeypatch)
        await pilot.press("s")
        assert [p.name for p in here.iterdir()] == [NAME]
        data = (here / NAME).read_bytes()
        assert len(app.strings) == 1500
        assert data == lines(app.strings)
        assert len(data.splitlines()) == 1500
        assert (record.toasts, record.severities) == ([f"Saved {NAME}"], ["information"])


async def test_s_never_overwrites(here: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    app = JumbleApp(Settings(count=1500))
    async with app.run_test() as pilot:
        record = Recorder(app, monkeypatch)
        await pilot.press("s")
        saved = (here / NAME).read_bytes()
        await pilot.press("g", "s")
        assert (here / NAME).read_bytes() == saved
        assert record.toasts[-1] == f"{NAME} exists; nothing saved"
        assert record.severities[-1] == "error"


@pytest.fixture
def read_only(here: Path) -> Iterator[Path]:
    here.chmod(0o500)
    try:
        yield here
    finally:
        here.chmod(0o700)


async def test_s_in_a_read_only_directory(read_only: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    app = JumbleApp(Settings(count=1500))
    async with app.run_test() as pilot:
        record = Recorder(app, monkeypatch)
        await pilot.press("s")
        assert list(read_only.iterdir()) == []
        assert record.toasts == [f"can't save {NAME}: Permission denied"]
        assert record.severities == ["error"]


class FullDisk:
    """A file opened as asked whose writes fail with ENOSPC."""

    def __init__(self, name: str, mode: str) -> None:
        self.file = open(name, mode)  # noqa: SIM115

    def __enter__(self) -> "FullDisk":
        return self

    def __exit__(self, *_: Any) -> None:
        self.file.close()

    def write(self, _data: bytes) -> int:
        raise OSError(errno.ENOSPC, "No space left on device")


async def test_a_failed_write_leaves_no_partial_file(
    here: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app = JumbleApp(Settings(count=1500))
    async with app.run_test() as pilot:
        record = Recorder(app, monkeypatch)
        monkeypatch.setattr(tui, "open", FullDisk, raising=False)
        await pilot.press("s")
        assert list(here.iterdir()) == []
        assert record.toasts == [f"can't save {NAME}: No space left on device"]
        assert record.severities == ["error"]


async def test_s_saves_emoji_as_utf8(here: Path) -> None:
    app = JumbleApp(Settings(count=3, charsets=(), custom="🐀🐁🐂"))
    async with app.run_test() as pilot:
        await pilot.press("s")
        data = (here / "jumble-1760000000-3.txt").read_bytes()
        assert data == lines(app.strings)
        assert set(data.decode("utf-8")) <= set("🐀🐁🐂\n")


async def test_s_while_invalid_saves_the_last_result(here: Path) -> None:
    app = JumbleApp(Settings(count=2))
    async with app.run_test() as pilot:
        last = list(app.strings)
        await set_value(pilot, "#length", "0")
        await set_value(pilot, "#count", "7")
        app.query_one("#results", OptionList).focus()
        await pilot.press("s")
        assert (here / "jumble-1760000000-2.txt").read_bytes() == lines(last)


async def test_s_before_any_strings_saves_nothing(
    here: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app = JumbleApp(Settings(length=0))
    async with app.run_test() as pilot:
        record = Recorder(app, monkeypatch)
        await pilot.press("s")
        assert list(here.iterdir()) == []
        assert record.toasts == []


# `d` saves the controls as the defaults (§7.4, DEC-18).


async def change_controls(pilot: Pilot[None]) -> None:
    await set_value(pilot, "#length", "24")
    await set_value(pilot, "#count", "3")
    await choose_only(pilot, "digits", "lower")
    await set_value(pilot, "#custom", "!?")
    await check(pilot, "#each")
    pilot.app.query_one("#results", OptionList).focus()


async def test_d_saves_the_controls(config_file: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    app = JumbleApp()
    async with app.run_test() as pilot:
        record = Recorder(app, monkeypatch)
        await change_controls(pilot)
        await pilot.press("d")
        saved = Settings(length=24, count=3, charsets=("lower", "digits"), custom="!?", each=True)
        assert app.settings() == saved
        assert load(config_file) == settings_dict(saved)
        assert record.toasts == [f"Saved defaults to {config_file}"]
        assert record.severities == ["information"]


async def test_d_while_invalid_saves_nothing(
    config_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app = JumbleApp(Settings(length=0))  # as `jumble -n 0 tui` starts
    async with app.run_test() as pilot:
        record = Recorder(app, monkeypatch)
        await pilot.press("d")
        assert not config_file.exists()
        assert (record.toasts, record.severities) == (["length must be at least 1"], ["error"])


async def test_d_while_invalid_after_a_change_names_the_banner(
    config_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app = JumbleApp()
    async with app.run_test() as pilot:
        record = Recorder(app, monkeypatch)
        await choose_only(pilot)
        app.query_one("#results", OptionList).focus()
        await pilot.press("d")
        assert not config_file.exists()
        assert banner(app) == "choose at least one character set"
        assert record.toasts == ["choose at least one character set"]
        # Valid again: `d` saves.
        await choose_only(pilot, "digits")
        await pilot.press("d")
        assert load(config_file)["charsets"] == ["digits"]
        assert record.toasts[-1] == f"Saved defaults to {config_file}"


async def test_d_repairs_the_file_the_tui_started_without(config_file: Path) -> None:
    # A broken file starts the TUI from the defaults and the command line's
    # options; `d` replaces the bad value (DEC-17, DEC-18).
    config_file.write_text("length = 0  # too short\n")
    with pytest.raises(JumbleError):
        load(config_file)
    app = JumbleApp(Settings(length=8), file_error=f"{config_file}: length: ...")
    async with app.run_test() as pilot:
        await pilot.press("d")
        assert load(config_file) == settings_dict(Settings(length=8))
        assert config_file.read_text().startswith("length = 8  # too short\n")


async def test_d_resolves_the_path_when_it_saves(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The path at the time of the save, not at start: a TUI started with
    # --no-config still saves (§7.4). As pathlib writes it (§5.1).
    app = JumbleApp()
    async with app.run_test() as pilot:
        record = Recorder(app, monkeypatch)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("JUMBLE_CONFIG", "./later/config.toml")
        await pilot.press("d")
        assert load(tmp_path / "later" / "config.toml") == settings_dict(Settings())
        assert record.toasts == ["Saved defaults to later/config.toml"]


async def test_d_when_the_file_cant_be_saved(
    config_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_file.mkdir()
    app = JumbleApp()
    async with app.run_test() as pilot:
        record = Recorder(app, monkeypatch)
        await pilot.press("d")
        assert app.is_running
        assert record.toasts == [f"can't save {config_file}: Is a directory"]
        assert record.severities == ["error"]


async def test_the_command_line_reads_what_d_saved(
    config_file: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    app = JumbleApp()
    async with app.run_test() as pilot:
        await change_controls(pilot)
        await pilot.press("d")
        saved = app.settings()
    capsys.readouterr()
    assert main(["--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["settings"] == settings_dict(saved)
    assert len(out["strings"]) == 3


# `,` opens the settings screen, a form on the settings file (§7.4, DEC-20).
# Its widgets are reached through `app.screen`: `app.query_one` searches the
# main screen (AGENTS.md, Testing notes). Its buttons always show, so they
# can be clicked at any size the dialog fits (§7.4, DEC-23).

SIZE = (100, 30)


async def open_settings(pilot: Pilot[None]) -> SettingsScreen:
    pilot.app.query_one("#results", OptionList).focus()
    await pilot.press("comma")
    await pilot.pause()
    screen = pilot.app.screen
    assert isinstance(screen, SettingsScreen)
    return screen


def form(app: App[None]) -> Settings:
    return read_controls(app.screen)


def form_selected(app: JumbleApp) -> list[str]:
    return list(app.screen.query_one("#charsets", SelectionList).selected)


async def set_form(pilot: Pilot[None], selector: str, value: str | bool) -> None:
    """Set a form input to a string, or a form checkbox to a boolean."""
    if isinstance(value, bool):
        pilot.app.screen.query_one(selector, Checkbox).value = value
    else:
        pilot.app.screen.query_one(selector, Input).value = value
    await pilot.pause()


async def choose_only_in_form(pilot: Pilot[None], *names: str) -> None:
    sets = pilot.app.screen.query_one("#charsets", SelectionList)
    sets.deselect_all()
    for name in names:
        sets.select(name)
    await pilot.pause()


def settings_screens(app: JumbleApp) -> int:
    return sum(isinstance(screen, SettingsScreen) for screen in app.screen_stack)


async def test_comma_opens_the_settings_screen() -> None:
    app = JumbleApp()
    async with app.run_test(size=SIZE) as pilot:
        await open_settings(pilot)
        assert settings_screens(app) == 1
        # Focus starts on the first control.
        assert app.focused is app.screen.query_one("#length", Input)


async def test_the_form_holds_the_main_screens_controls() -> None:
    app = JumbleApp()
    async with app.run_test(size=SIZE) as pilot:
        await open_settings(pilot)
        screen = app.screen
        for selector, title in (
            ("#length", "Length"),
            ("#count", "Count"),
            ("#charsets", "Sets"),
            ("#custom", "Custom"),
        ):
            assert screen.query_one(selector).border_title == title
            assert app.query_one(selector).border_title == title
        for wid, label, _ in tui.OPTIONS:
            assert str(screen.query_one(f"#{wid}", Checkbox).label) == label
        sets = screen.query_one("#charsets", SelectionList)
        assert [sets.get_option_at_index(i).value for i in range(sets.option_count)] == list(
            CHARSETS
        )


async def test_the_form_is_filled_from_the_file_not_the_main_screen(config_file: Path) -> None:
    config_file.write_text('length = 24\ncustom = "abc"\n')
    app = JumbleApp(Settings(length=8))  # as `jumble -n 8 tui` starts
    async with app.run_test(size=SIZE) as pilot:
        await open_settings(pilot)
        screen = app.screen
        assert screen.query_one("#length", Input).value == "24"
        assert form_selected(app) == []
        assert screen.query_one("#custom", Input).value == "abc"
        assert form(app) == Settings(length=24, charsets=(), custom="abc")
        assert app.query_one("#length", Input).value == "8"
        assert app.settings() == Settings(length=8)


@pytest.mark.parametrize("text", [None, "charsets = []\n"])
async def test_a_file_choosing_no_characters_fills_the_defaults(
    config_file: Path, text: str | None
) -> None:
    if text is not None:
        config_file.write_text(text)
    app = JumbleApp(Settings(length=8, charsets=("digits",)))
    async with app.run_test(size=SIZE) as pilot:
        await open_settings(pilot)
        assert form(app) == Settings()
        assert form_selected(app) == ["lower", "upper", "digits"]


FILES = [
    None,
    "charsets = []\n",
    'length = 24\ncustom = "abc"\n',
    'length = 12\ncount = 4\ncharsets = ["digits", "greek"]\ncustom = "!?"\n'
    "no_ambiguous = true\neach = true\nno_repeat = true\nunique = true\n",
]


@pytest.mark.parametrize("text", FILES)
async def test_the_form_and_the_command_line_merge_a_file_alike(
    config_file: Path, text: str | None
) -> None:
    # One merge (§5.2): the command line with no options, the form, and
    # `file_settings` agree on every file.
    if text is not None:
        config_file.write_text(text)
    file = load(config_file)
    assert settings_from(parser().parse_args([]), file) == file_settings(file)
    app = JumbleApp()
    async with app.run_test(size=SIZE) as pilot:
        await open_settings(pilot)
        assert form(app) == file_settings(file)


async def test_the_form_shows_the_files_path(config_file: Path) -> None:
    app = JumbleApp()
    async with app.run_test(size=SIZE) as pilot:
        await open_settings(pilot)
        assert str(app.screen.query_one("#path", Static).content) == str(config_file)


async def test_the_form_shows_the_path_as_pathlib_writes_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("JUMBLE_CONFIG", "./rel/config.toml")
    app = JumbleApp()
    async with app.run_test(size=SIZE) as pilot:
        await open_settings(pilot)
        assert str(app.screen.query_one("#path", Static).content) == "rel/config.toml"


async def test_an_invalid_file_fills_the_defaults_and_save_repairs_it(
    config_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_file.write_text("length = 0\n")
    app = JumbleApp()
    async with app.run_test(size=SIZE) as pilot:
        record = Recorder(app, monkeypatch)
        await open_settings(pilot)
        assert form(app) == Settings()
        assert record.toasts == [f"{config_file}: length: length must be at least 1"]
        assert record.severities == ["error"]
        await pilot.click("#save")
        await pilot.pause()
        assert load(config_file) == settings_dict(Settings())
        assert record.toasts[-1] == f"Saved defaults to {config_file}"


async def test_a_file_that_cant_be_read_or_saved(
    config_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_file.mkdir()
    app = JumbleApp(Settings(length=8))
    async with app.run_test(size=SIZE) as pilot:
        record = Recorder(app, monkeypatch)
        await open_settings(pilot)
        assert form(app) == Settings()
        assert record.toasts == [f"can't read {config_file}: Is a directory"]
        await pilot.click("#save")
        await pilot.pause()
        assert record.toasts[-1] == f"can't save {config_file}: Is a directory"
        assert record.severities == ["error", "error"]
        assert settings_screens(app) == 1
        assert app.settings() == Settings(length=8)


async def change_form(pilot: Pilot[None]) -> Settings:
    """Set every form control away from the defaults; the settings they hold."""
    await set_form(pilot, "#length", "20")
    await set_form(pilot, "#count", "4")
    await choose_only_in_form(pilot, "lower", "greek")
    await set_form(pilot, "#custom", "!?")
    for wid, _, _ in tui.OPTIONS:
        await set_form(pilot, f"#{wid}", True)
    saved = Settings(20, 4, ("lower", "greek"), "!?", True, True, True, True)
    assert form(pilot.app) == saved
    return saved


async def test_save_writes_the_file_and_sets_the_main_screen(
    config_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app = JumbleApp(Settings(count=3))
    async with app.run_test(size=SIZE) as pilot:
        record = Recorder(app, monkeypatch)
        strings = list(app.strings)
        await open_settings(pilot)
        saved = await change_form(pilot)
        await pilot.click("#save")
        await pilot.pause()
        assert settings_screens(app) == 0
        assert load(config_file) == settings_dict(saved)
        assert app.settings() == saved
        assert banner(app) is None
        assert app.sub_title == strength_line(strength(saved))
        # No jumble: the results stay (§7.1).
        assert app.strings == strings
        assert (record.toasts, record.severities) == (
            [f"Saved defaults to {config_file}"],
            ["information"],
        )


async def test_save_clears_the_banner(config_file: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    app = JumbleApp(Settings(length=0))
    async with app.run_test(size=SIZE) as pilot:
        assert banner(app) == "length must be at least 1"
        # The banner and the subtitle as the toast shows: already the saved values'.
        seen: list[tuple[str, str | None, str]] = []
        monkeypatch.setattr(
            app, "notify", lambda message, **_: seen.append((message, banner(app), app.sub_title))
        )
        await open_settings(pilot)
        await pilot.click("#save")
        await pilot.pause()
        assert seen == [(f"Saved defaults to {config_file}", None, VALID)]
        assert app.settings() == Settings()
        assert banner(app) is None
        assert app.sub_title == VALID
        assert app.strings == []


async def test_save_resolves_the_path_when_it_saves(
    tmp_path: Path, config_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The path at the time of the save, not when the screen opened (§7.4).
    app = JumbleApp()
    async with app.run_test(size=SIZE) as pilot:
        record = Recorder(app, monkeypatch)
        await open_settings(pilot)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("JUMBLE_CONFIG", "./later/config.toml")
        await pilot.click("#save")
        await pilot.pause()
        assert not config_file.exists()
        assert load(tmp_path / "later" / "config.toml") == settings_dict(Settings())
        assert record.toasts == ["Saved defaults to later/config.toml"]


async def test_enter_in_a_form_input_saves_and_doesnt_jumble(
    config_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The form's `Input.Submitted` would reach `JumbleApp.on_input_submitted`
    # and jumble, if the screen let it bubble on.
    app = JumbleApp(Settings(count=3))
    async with app.run_test(size=SIZE) as pilot:
        record = Recorder(app, monkeypatch)
        strings = list(app.strings)
        await open_settings(pilot)
        saved = await change_form(pilot)
        app.screen.query_one("#custom", Input).focus()
        await pilot.press("enter")
        await pilot.pause()
        assert settings_screens(app) == 0
        assert load(config_file) == settings_dict(saved)
        assert app.settings() == saved
        assert app.strings == strings
        assert record.toasts == [f"Saved defaults to {config_file}"]


async def test_the_form_doesnt_reach_the_main_screen_until_save() -> None:
    app = JumbleApp()
    async with app.run_test(size=SIZE) as pilot:
        await open_settings(pilot)
        await set_form(pilot, "#length", "0")
        await choose_only_in_form(pilot)
        await set_form(pilot, "#each", True)
        assert banner(app) is None
        assert app.sub_title == VALID
        assert app.settings() == Settings()


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"#length": "0"}, "length must be at least 1"),
        (
            {"#length": "2", "#each": True},
            "length must be at least 3 to take one character from each of 3 sets",
        ),
    ],
)
async def test_an_invalid_form_saves_nothing(
    config_file: Path,
    monkeypatch: pytest.MonkeyPatch,
    changes: dict[str, str | bool],
    message: str,
) -> None:
    app = JumbleApp()
    async with app.run_test(size=SIZE) as pilot:
        record = Recorder(app, monkeypatch)
        await open_settings(pilot)
        for selector, value in changes.items():
            await set_form(pilot, selector, value)
        await pilot.click("#save")
        await pilot.pause()
        assert not config_file.exists()
        assert settings_screens(app) == 1
        assert (record.toasts, record.severities) == ([message], ["error"])
        assert app.settings() == Settings()


@pytest.mark.parametrize("how", ["cancel", "escape"])
async def test_cancel_and_escape_change_nothing(
    config_file: Path, monkeypatch: pytest.MonkeyPatch, how: str
) -> None:
    config_file.write_text("# mine\nlength = 24\n")
    before = config_file.read_bytes()
    app = JumbleApp(Settings(length=8))
    async with app.run_test(size=SIZE) as pilot:
        record = Recorder(app, monkeypatch)
        await open_settings(pilot)
        await change_form(pilot)
        if how == "cancel":
            await pilot.click("#cancel")
        else:
            app.screen.query_one("#custom", Input).focus()
            await pilot.press("escape")
        await pilot.pause()
        assert settings_screens(app) == 0
        assert config_file.read_bytes() == before
        assert app.settings() == Settings(length=8)
        assert record.toasts == []


async def test_main_screen_keys_dont_act_in_the_form(
    here: Path, config_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app = JumbleApp(Settings(count=3))
    async with app.run_test(size=SIZE) as pilot:
        record = Recorder(app, monkeypatch)
        strings = list(app.strings)
        await open_settings(pilot)
        app.screen.query_one("#each", Checkbox).focus()
        await pilot.press("g", "c", "a", "s", "d", "comma", "q")
        await pilot.pause()
        assert app.is_running
        assert settings_screens(app) == 1
        assert isinstance(app.screen, SettingsScreen)
        assert app.strings == strings
        assert list(here.iterdir()) == []
        assert not config_file.exists()
        assert (record.copied, record.toasts) == ([], [])
        assert app.screen.query_one("#each", Checkbox).value is False


async def test_the_save_button_is_a_button() -> None:
    app = JumbleApp()
    async with app.run_test(size=SIZE) as pilot:
        await open_settings(pilot)
        assert str(app.screen.query_one("#save", Button).label) == "Save"
        assert str(app.screen.query_one("#cancel", Button).label) == "Cancel"


# The path and the buttons always show; only the form scrolls (§7.4, DEC-23).
# A widget scrolled out of the form keeps a region outside it, so "in view"
# is checked against the form's region, and the buttons against the screen's.


@pytest.fixture
def long_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A settings path of 140 characters with no spaces, missing until saved.

    It wraps to three lines at the dialog's width, with or without the
    form's scrollbar.
    """
    head, tail = f"{tmp_path}/", "/config.toml"
    path = Path(head + "d" * (140 - len(head) - len(tail)) + tail)
    assert len(str(path)) == 140
    monkeypatch.setenv("JUMBLE_CONFIG", str(path))
    return path


def path_lines(screen: SettingsScreen) -> list[str]:
    return [line.rstrip() for line in rendered(screen.query_one("#path")).splitlines()]


def regions(screen: SettingsScreen, *selectors: str) -> list[Region]:
    return [screen.query_one(selector).region for selector in selectors]


def buttons_show(app: JumbleApp, screen: SettingsScreen) -> bool:
    return all(app.screen.region.contains_region(r) for r in regions(screen, "#save", "#cancel"))


async def test_a_long_path_shows_whole_above_the_buttons(long_path: Path) -> None:
    app = JumbleApp()
    async with app.run_test(size=SIZE) as pilot:
        screen = await open_settings(pilot)
        lines = path_lines(screen)
        assert len(lines) == 3
        assert "".join(lines) == str(long_path)
        assert buttons_show(app, screen)
        await pilot.click("#save")
        await pilot.pause()
        assert settings_screens(app) == 0
        assert load(long_path) == settings_dict(Settings())


async def test_only_the_form_scrolls_on_a_short_terminal(long_path: Path) -> None:
    app = JumbleApp()
    async with app.run_test(size=(100, 16)) as pilot:
        screen = await open_settings(pilot)
        assert "".join(path_lines(screen)) == str(long_path)
        assert buttons_show(app, screen)
        form = screen.query_one("#form")
        assert form.virtual_size.height > form.region.height
        pinned = regions(screen, "#path", "#save", "#cancel")
        for selector in ("#unique", "#length"):
            screen.query_one(selector).focus()
            await pilot.pause()
            await pilot.wait_for_scheduled_animations()
            assert form.region.contains_region(screen.query_one(selector).region), selector
            assert regions(screen, "#path", "#save", "#cancel") == pinned, selector
        await pilot.click("#cancel")
        await pilot.pause()
        assert settings_screens(app) == 0
        assert not long_path.exists()


# Every label shows whole at 100 by 30, `One from each set` included (§7.1, #12).


def rendered(widget: Widget) -> str:
    """The text `widget` draws in its region, its border included."""
    size = widget.region
    return "\n".join(s.text for s in widget.render_lines(Region(0, 0, size.width, size.height)))


LABELS = [(f"#{wid}", label) for wid, label, _ in tui.OPTIONS] + [
    ("#length", "Length"),
    ("#count", "Count"),
    ("#charsets", "Sets"),
    ("#custom", "Custom"),
]


async def test_every_label_shows_whole() -> None:
    app = JumbleApp()
    async with app.run_test(size=SIZE) as pilot:
        for screen in (app.screen, await open_settings(pilot)):
            for selector, label in LABELS:
                text = rendered(screen.query_one(selector))
                assert label in text, selector
                assert "…" not in text, selector


# Under the Sets list, a preview shows the set under that list's cursor, as
# §2.1 defines it; the form has its own, following its own list (§7.6,
# DEC-22).

PREVIEWED = ("symbols", "space", "emoji-faces", "greek")


def preview(node: Any) -> str:
    """The preview's text under `node` as it draws, its wrapped lines joined."""
    return "".join(line.rstrip() for line in rendered(node.query_one("#preview")).splitlines())


def test_characters_are_the_set_as_defined() -> None:
    for name, chars in CHARSETS.items():
        assert characters(name) == ("(the space character)" if name == "space" else chars), name


async def move_to(pilot: Pilot[None], sets: SelectionList[str], name: str) -> None:
    """Move `sets`' cursor to `name` by key; it is focused, and `name` is below it."""
    target = list(CHARSETS).index(name)
    while sets.highlighted != target:
        await pilot.press("down")
    await pilot.pause()


async def test_the_preview_starts_on_lower() -> None:
    app = JumbleApp()
    async with app.run_test(size=SIZE):
        assert app.query_one("#charsets", SelectionList).highlighted == 0
        assert preview(app.screen) == string.ascii_lowercase


async def test_the_preview_follows_the_cursor_by_key() -> None:
    app = JumbleApp()
    async with app.run_test(size=SIZE) as pilot:
        sets = app.query_one("#charsets", SelectionList)
        sets.focus()
        for name in PREVIEWED:
            await move_to(pilot, sets, name)
            assert preview(app.screen) == characters(name), name
            if name == "symbols":
                # Text, not markup: `[` and `\` show as themselves.
                assert preview(app.screen) == string.punctuation
        await pilot.press("end")
        await pilot.pause()
        assert preview(app.screen) == characters("box")


async def test_four_lines_hold_the_largest_sets() -> None:
    app = JumbleApp()
    async with app.run_test(size=SIZE) as pilot:
        sets = app.query_one("#charsets", SelectionList)
        shown = app.query_one("#preview", Static)
        for name in ("emoji-faces", "box"):
            sets.highlighted = list(CHARSETS).index(name)
            await pilot.pause()
            lines = rendered(shown).splitlines()
            assert shown.region.height == 4, name
            assert len(lines) == 4, name
            # The fourth line holds the last of the set: nothing is cut.
            assert lines[3].strip(), name
            assert preview(app.screen) == CHARSETS[name], name


async def test_the_preview_follows_a_click() -> None:
    app = JumbleApp()
    async with app.run_test(size=SIZE) as pilot:
        # Row 0 is the list's border, so row k + 1 is set k.
        await pilot.click("#charsets", offset=(4, 3))
        await pilot.pause()
        assert app.query_one("#charsets", SelectionList).highlighted == 2
        assert preview(app.screen) == characters("digits")


async def test_the_preview_ignores_the_other_controls() -> None:
    app = JumbleApp()
    async with app.run_test(size=SIZE) as pilot:
        await check(pilot, "#no-ambiguous")
        await set_value(pilot, "#custom", "abc")
        # `l` and `o` are look-alikes, but the preview shows the set (DEC-22).
        assert preview(app.screen) == string.ascii_lowercase


async def test_checking_a_set_keeps_the_preview() -> None:
    app = JumbleApp()
    async with app.run_test(size=SIZE) as pilot:
        sets = app.query_one("#charsets", SelectionList)
        sets.focus()
        await move_to(pilot, sets, "greek")
        for checked in (True, False):
            await pilot.press("space")
            await pilot.pause()
            assert ("greek" in sets.selected) is checked
            assert sets.highlighted == list(CHARSETS).index("greek")
            assert preview(app.screen) == characters("greek")


async def test_the_form_has_its_own_preview() -> None:
    app = JumbleApp()
    async with app.run_test(size=SIZE) as pilot:
        sets = app.query_one("#charsets", SelectionList)
        sets.focus()
        await move_to(pilot, sets, "greek")
        screen = await open_settings(pilot)
        assert preview(screen) == string.ascii_lowercase
        form_sets = screen.query_one("#charsets", SelectionList)
        form_sets.focus()
        await move_to(pilot, form_sets, "upper")
        assert preview(screen) == string.ascii_uppercase
        # The form's cursor never moves the main screen's preview.
        assert preview(app.main) == characters("greek")
        await pilot.click("#cancel")
        await pilot.pause()
        assert settings_screens(app) == 0
        assert preview(app.screen) == characters("greek")


async def test_the_controls_fit_with_the_preview() -> None:
    app = JumbleApp()
    async with app.run_test(size=SIZE):
        pane = app.query_one("#controls")
        options = [f"#{wid}" for wid, _, _ in tui.OPTIONS]
        for selector in ["#length", "#count", "#charsets", "#preview", "#custom", *options]:
            assert pane.region.contains_region(app.query_one(selector).region), selector
        assert pane.max_scroll_y == 0


# Help shows §2.1's sets and §7.6's notes, independently of the current alphabet.
HELP_HEADINGS = [
    "lower · 26 characters",
    "upper · 26 characters",
    "digits · 10 characters",
    "symbols · 32 characters",
    "space · 1 character",
    "chess · 12 characters",
    "cards · 52 characters",
    "dice · 6 characters",
    "emoji-faces · 80 characters",
    "emoji-animals · 63 characters",
    "emoji-food · 55 characters",
    "greek · 48 characters",
    "cyrillic · 64 characters",
    "latin-accented · 62 characters",
    "arrows · 10 characters",
    "math · 26 characters",
    "currency · 12 characters",
    "box · 160 characters",
]
HELP_NOTES = [
    "Length: characters per string, at least 1",
    "Count: how many strings, at least 1",
    "Custom: extra characters, drawn as one more set",
    "No look-alikes: leave out 0 O o l 1 I | ` ' \" ; : . , -",
    "One from each set: at least one character from every chosen set",
    "No repeats: no character twice within a string",
    "All unique: no string twice in the output",
]


async def open_help(pilot: Pilot[None]) -> HelpScreen:
    await pilot.press("?")
    await pilot.pause()
    assert isinstance(pilot.app.screen, HelpScreen)
    return pilot.app.screen


def main_snapshot(app: JumbleApp) -> tuple[object, ...]:
    """Everything Help must leave alone (§7.6), including both cursors."""
    return (
        app.settings(),
        list(app.strings),
        results(app),
        app.query_one("#results", OptionList).highlighted,
        banner(app),
        app.problem,
        app.valid,
        app.sub_title,
        preview(app.main),
        app.query_one("#charsets", SelectionList).highlighted,
    )


async def test_help_lists_every_set_and_control_note() -> None:
    app = JumbleApp()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.pause()
        assert app.focused is app.query_one("#results")
        footer = "".join(rendered(w) for w in app.query_one(Footer).query(Widget))
        assert "? Help" in footer
        screen = await open_help(pilot)
        assert screen.query_one("#help-content").border_title == "Help"
        headings = list(screen.query(".set-heading").results(Static))
        bodies = list(screen.query(".set-body").results(Static))
        notes = list(screen.query(".control-note").results(Static))
        assert [str(w.content) for w in headings] == HELP_HEADINGS
        assert [str(w.content) for w in bodies] == [characters(name) for name in CHARSETS]
        assert [str(w.content) for w in notes] == HELP_NOTES
        # Sets alternate heading/body, with all notes after the last set.
        children = list(screen.query_one("#help-content").children)
        assert children == [w for pair in zip(headings, bodies, strict=True) for w in pair] + notes
        for note, expected in zip(notes, HELP_NOTES, strict=True):
            note.scroll_visible(animate=False)
            await pilot.pause()
            assert screen.query_one("#help-content").content_region.contains_region(note.region)
            assert " ".join(rendered(note).split()) == expected


@pytest.mark.parametrize("name", ["symbols", "space", "emoji-faces", "box"])
async def test_help_renders_complete_wrapped_bodies(name: str) -> None:
    app = JumbleApp()
    async with app.run_test(size=SIZE) as pilot:
        screen = await open_help(pilot)
        body = list(screen.query(".set-body").results(Static))[list(CHARSETS).index(name)]
        body.scroll_visible(animate=False)
        await pilot.pause()
        content = screen.query_one("#help-content")
        assert content.content_region.contains_region(body.region)
        drawn = "".join(line.rstrip() for line in rendered(body).splitlines())
        assert drawn == characters(name)
        if name in ("emoji-faces", "box"):
            assert body.region.height > 1
            assert drawn[-1] == CHARSETS[name][-1]


async def test_help_ignores_alphabet_filters() -> None:
    app = JumbleApp()
    async with app.run_test(size=SIZE) as pilot:
        await check(pilot, "#no-ambiguous")
        await set_value(pilot, "#custom", "abc")
        screen = await open_help(pilot)
        bodies = [str(w.content) for w in screen.query(".set-body").results(Static)]
        assert bodies == [characters(name) for name in CHARSETS]
        assert bodies[0] == string.ascii_lowercase
        assert "l" in bodies[0] and "o" in bodies[0]


async def test_help_uses_the_shared_renderer(monkeypatch: pytest.MonkeyPatch) -> None:
    app = JumbleApp()
    async with app.run_test(size=SIZE) as pilot:
        renderer = Mock(side_effect=lambda name: f"rendered {name}")
        monkeypatch.setattr(tui, "characters", renderer)
        screen = await open_help(pilot)
        assert [call.args for call in renderer.call_args_list] == [(name,) for name in CHARSETS]
        assert [str(w.content) for w in screen.query(".set-body").results(Static)] == [
            f"rendered {name}" for name in CHARSETS
        ]


@pytest.mark.parametrize("key", ["escape", "?"])
async def test_closing_help_preserves_the_main_screen(key: str) -> None:
    app = JumbleApp(Settings(count=3))
    async with app.run_test(size=SIZE) as pilot:
        sets = app.query_one("#charsets", SelectionList)
        sets.highlighted = list(CHARSETS).index("greek")
        await pilot.pause()
        await pilot.press("down")
        assert app.query_one("#results", OptionList).highlighted == 1
        before = main_snapshot(app)
        await open_help(pilot)
        await pilot.press("pagedown")
        await pilot.press(key)
        await pilot.pause()
        assert len(app.screen_stack) == 1
        assert main_snapshot(app) == before


@pytest.mark.parametrize("key", ["g", "c", "a", "s", "d", "comma", "q"])
async def test_main_actions_are_inert_in_help(
    key: str, here: Path, config_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app = JumbleApp(Settings(count=3))
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("down")
        assert app.valid and len(app.strings) == 3
        assert app.query_one("#results", OptionList).highlighted == 1
        before = main_snapshot(app)
        # Install after startup, which must generate. Observe effects as well
        # as state: a leaked jumble is caught even if its strings stay equal.
        spies = [Mock(wraps=tui.generate), Mock(), Mock(), Mock(), Mock(), Mock()]
        for target, attr, spy in zip(
            [tui, app, tui, tui, app, app],
            ["generate", "copy_to_clipboard", "open", "save", "action_settings", "exit"],
            spies,
            strict=True,
        ):
            monkeypatch.setattr(target, attr, spy, raising=False)
        screen = await open_help(pilot)
        await pilot.press(key)
        await pilot.pause()
        for spy in spies:
            spy.assert_not_called()
        assert app.screen is screen and app.is_running
        assert main_snapshot(app) == before
        assert list(here.iterdir()) == [] and not config_file.exists()


@pytest.mark.parametrize("had_results", [False, True])
async def test_help_opens_with_invalid_controls_and_preserves_results(had_results: bool) -> None:
    app = JumbleApp(Settings(length=16 if had_results else 0, count=3))
    async with app.run_test(size=SIZE) as pilot:
        if had_results:
            await pilot.press("down")
            await set_value(pilot, "#length", "0")
        assert banner(app) == "length must be at least 1"
        assert bool(app.strings) is had_results
        before = main_snapshot(app)
        await open_help(pilot)
        await pilot.press("escape")
        await pilot.pause()
        assert len(app.screen_stack) == 1
        assert main_snapshot(app) == before


async def test_question_mark_is_typed_in_main_and_settings_inputs() -> None:
    app = JumbleApp()
    async with app.run_test(size=SIZE) as pilot:
        custom = app.query_one("#custom", Input)
        custom.focus()
        await pilot.press("?")
        assert custom.value == "?"
        assert len(app.screen_stack) == 1
        await pilot.press("escape")
        screen = await open_settings(pilot)
        form_custom = screen.query_one("#custom", Input)
        form_custom.focus()
        await pilot.press("?")
        assert form_custom.value == "?"
        assert app.screen is screen and custom.value == "?"
        # With a non-input focused, Settings has no Help binding either.
        screen.query_one("#each", Checkbox).focus()
        await pilot.press("?")
        assert app.screen is screen


async def test_help_scrolls_by_arrows_pages_and_mouse_to_the_last_note() -> None:
    app = JumbleApp()
    async with app.run_test(size=SIZE) as pilot:
        screen = await open_help(pilot)
        content = screen.query_one("#help-content", VerticalScroll)
        assert app.focused is content and content.scroll_y == 0
        await pilot.press("down")
        await pilot.wait_for_scheduled_animations()
        after_down = content.scroll_y
        assert after_down > 0
        await pilot.press("pagedown")
        await pilot.wait_for_scheduled_animations()
        assert content.scroll_y > after_down
        await pilot.press("pageup")
        await pilot.wait_for_scheduled_animations()
        assert content.scroll_y <= after_down
        await pilot.press("up")
        await pilot.wait_for_scheduled_animations()
        assert content.scroll_y == 0
        # Deliver a wheel event at the scroll container, as a terminal driver
        # does; Pilot has no wheel helper in this Textual version.
        content.post_message(events.MouseScrollDown(content, 3, 3, 0, 0, 0, False, False, False))
        await pilot.pause()
        await pilot.wait_for_scheduled_animations()
        assert content.scroll_y > 0
        for _ in range(20):
            await pilot.press("pagedown")
            await pilot.wait_for_scheduled_animations()
            if content.scroll_y == content.max_scroll_y:
                break
        assert content.scroll_y == content.max_scroll_y
        note = list(screen.query(".control-note").results(Static))[-1]
        assert content.content_region.contains_region(note.region)
        assert "".join(line.rstrip() for line in rendered(note).splitlines()) == HELP_NOTES[-1]
