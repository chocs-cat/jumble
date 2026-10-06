"""The interactive generator: pick a length and character sets, then jumble."""

from typing import ClassVar

from textual.app import App, ComposeResult
from textual.binding import BindingType
from textual.containers import Horizontal
from textual.widgets import Button, Checkbox, Footer, Input, Static

from jumble.generate import Settings, generate

# The sets offered here until D3 rebuilds the TUI; all eighteen would not fit the row.
SETS = ("lower", "upper", "digits", "symbols")


class JumbleApp(App[None]):
    TITLE = "jumble"
    # The length input would swallow the letter bindings, so start on the button.
    AUTO_FOCUS = "#jumble"
    CSS = """
    Screen { align: center middle; }
    #result { width: auto; padding: 1 2; border: round $accent; text-style: bold; }
    #controls { height: auto; width: auto; margin: 1 0; }
    #length { width: 12; }
    #error { color: $error; height: 1; }
    """
    BINDINGS: ClassVar[list[BindingType]] = [
        ("g", "jumble", "Jumble"),
        ("c", "copy", "Copy"),
        ("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Static(id="result")
        with Horizontal(id="controls"):
            yield Input("16", id="length", type="integer", tooltip="Length")
            for name in SETS:
                yield Checkbox(name, name != "symbols", id=name)
            yield Checkbox("no look-alikes", id="no-ambiguous")
            yield Button("Jumble", id="jumble", variant="primary")
        yield Static(id="error")
        yield Footer()

    def on_mount(self) -> None:
        self.action_jumble()

    def on_button_pressed(self) -> None:
        self.action_jumble()

    def on_input_submitted(self) -> None:
        self.action_jumble()

    def action_jumble(self) -> None:
        error = self.query_one("#error", Static)
        try:
            settings = Settings(
                length=int(self.query_one("#length", Input).value or 0),
                charsets=tuple(n for n in SETS if self.query_one(f"#{n}", Checkbox).value),
                no_ambiguous=self.query_one("#no-ambiguous", Checkbox).value,
            )
            text = generate(settings)[0]
        except ValueError as e:
            error.update(str(e))
            return
        error.update("")
        self.query_one("#result", Static).update(text)

    def action_copy(self) -> None:
        self.copy_to_clipboard(str(self.query_one("#result", Static).content))
        self.notify("Copied")
