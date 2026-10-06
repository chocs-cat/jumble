from textual.widgets import Checkbox, Input, Static

from jumble.tui import JumbleApp


async def test_jumble_uses_controls() -> None:
    app = JumbleApp()
    async with app.run_test() as pilot:
        app.query_one("#length", Input).value = "24"
        for name in ("lower", "upper"):
            app.query_one(f"#{name}", Checkbox).value = False
        await pilot.press("g")
        await pilot.pause()
        result = str(app.query_one("#result", Static).content)
        assert len(result) == 24
        assert result.isdigit()
