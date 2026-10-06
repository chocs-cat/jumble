from importlib.metadata import version

import pytest
from textual.pilot import Pilot
from textual.widgets import Checkbox, Input, OptionList, SelectionList, Static

from jumble import tui
from jumble.generate import CHARSETS, JumbleError, Settings
from jumble.tui import JumbleApp


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
        assert app.title == f"jumble {version('jumble')}"
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
        assert shown == [("g", "Jumble"), ("c", "Copy"), ("a", "Copy all"), ("q", "Quit")]


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
