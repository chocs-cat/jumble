from importlib.metadata import version

from textual.pilot import Pilot
from textual.widgets import Checkbox, Input, OptionList, SelectionList, Static

from jumble.generate import CHARSETS
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
