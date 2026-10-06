"""The interactive generator (docs/spec.md §7): controls beside results, live validation."""

from importlib.metadata import version
from typing import ClassVar

from textual.app import App, ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Grid, Horizontal, VerticalScroll
from textual.widgets import Checkbox, Footer, Header, Input, OptionList, SelectionList, Static
from textual.widgets.option_list import Option

from jumble.generate import CHARSETS, JumbleError, Settings, generate, strength, strength_line

DEFAULTS = Settings()

# The results pane lists at most this many strings (§7.1, DEC-11).
SHOWN = 1000

# The four options' checkboxes: widget ID, label (§7.1), and setting name.
OPTIONS = (
    ("no-ambiguous", "No look-alikes", "no_ambiguous"),
    ("each", "One from each set", "each"),
    ("no-repeat", "No repeats", "no_repeat"),
    ("unique", "All unique", "unique"),
)


# Each input and the set list are labelled in their border.
TITLES = (("#length", "Length"), ("#count", "Count"), ("#charsets", "Sets"), ("#custom", "Custom"))


def parse_int(value: str) -> int:
    """An integer input's value; one that doesn't parse (empty, `-`) counts as 0 (§7.1)."""
    try:
        return int(value)
    except ValueError:
        return 0


class JumbleApp(App[None]):
    # The results pane holds focus so letter keys reach the bindings (DEC-12).
    AUTO_FOCUS = "#results"
    CSS = """
    #error { display: none; background: $error; color: $text; padding: 0 1; }
    #error.shown { display: block; }
    #controls { width: 50; border-right: solid $panel; }
    #numbers { height: auto; }
    #numbers Input { width: 1fr; }
    #charsets { height: 12; }
    #options { grid-size: 2; height: auto; }
    #options Checkbox { width: 1fr; }
    #results { width: 1fr; height: 1fr; border: none; }
    """
    BINDINGS: ClassVar[list[BindingType]] = [
        ("g", "jumble", "Jumble"),
        ("c", "copy", "Copy"),
        ("a", "copy_all", "Copy all"),
        ("q", "quit", "Quit"),
        Binding("escape", "focus_results", show=False),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.title = f"jumble {version('jumble')}"
        self.strings: list[str] = []
        self.valid = False

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(id="error")
        with Horizontal():
            with VerticalScroll(id="controls"):
                with Horizontal(id="numbers"):
                    yield Input(str(DEFAULTS.length), id="length", type="integer")
                    yield Input(str(DEFAULTS.count), id="count", type="integer")
                yield SelectionList[str](
                    *((name, name, name in DEFAULTS.charsets) for name in CHARSETS),
                    id="charsets",
                )
                yield Input(DEFAULTS.custom, id="custom")
                with Grid(id="options"):
                    for widget_id, label, setting in OPTIONS:
                        yield Checkbox(label, getattr(DEFAULTS, setting), id=widget_id)
            # Strings can hold `[`, so they are shown as text, not markup.
            yield OptionList(id="results", markup=False)
        yield Footer()

    def on_mount(self) -> None:
        for selector, title in TITLES:
            self.query_one(selector).border_title = title
        self.check()
        self.action_jumble()

    def settings(self) -> Settings:
        """The controls as one `Settings`, unvalidated and with no default fill (§7.1)."""
        selected = set(self.query_one("#charsets", SelectionList).selected)
        options = {
            setting: self.query_one(f"#{wid}", Checkbox).value for wid, _, setting in OPTIONS
        }
        return Settings(
            length=parse_int(self.query_one("#length", Input).value),
            count=parse_int(self.query_one("#count", Input).value),
            charsets=tuple(name for name in CHARSETS if name in selected),
            custom=self.query_one("#custom", Input).value,
            **options,
        )

    def check(self) -> None:
        """Validate the controls: set the subtitle, or show the §6 message (§7.1)."""
        error = self.query_one("#error", Static)
        try:
            line = strength_line(strength(self.settings()))
        except JumbleError as e:
            self.valid = False
            self.sub_title = ""
            error.update(str(e))
            error.add_class("shown")
            return
        self.valid = True
        self.sub_title = line
        error.remove_class("shown")

    def on_input_changed(self) -> None:
        self.check()

    def on_checkbox_changed(self) -> None:
        self.check()

    def on_selection_list_selected_changed(self) -> None:
        self.check()

    def on_input_submitted(self) -> None:
        # `enter` in an input jumbles, as `g` would, and leaves the input (§7.2, DEC-12).
        self.action_jumble()
        self.action_focus_results()

    def action_focus_results(self) -> None:
        self.query_one("#results", OptionList).focus()

    def action_jumble(self) -> None:
        """Generate with the controls and replace the results; nothing while invalid."""
        if not self.valid:
            return
        try:
            strings = generate(self.settings())
        except JumbleError as e:
            # Only `unique`'s give-up gets past `check`: a toast, and the last
            # result, rows, and cursor stay; the banner is for the controls (§7.1, DEC-15).
            self.notify(str(e), severity="error")
            return
        self.strings = strings
        rows: list[str | Option] = list(self.strings[:SHOWN])
        if len(self.strings) > SHOWN:
            # Disabled, so the cursor skips it (§7.1, DEC-11).
            more = len(self.strings) - SHOWN
            rows.append(Option(f"… and {more} more (s saves all)", disabled=True))
        pane = self.query_one("#results", OptionList)
        pane.set_options(rows)
        pane.highlighted = 0

    # Copying uses the last jumble's strings, valid controls or not; before
    # any jumble there is nothing to copy (§7.1, §7.2).

    def action_copy(self) -> None:
        index = self.query_one("#results", OptionList).highlighted
        if not self.strings or index is None:
            return
        self.copy_to_clipboard(self.strings[index])
        self.notify("Copied")

    def action_copy_all(self) -> None:
        """Copy every string, those past the shown 1000 too (DEC-11)."""
        if not self.strings:
            return
        self.copy_to_clipboard("\n".join(self.strings))
        n = len(self.strings)
        self.notify(f"Copied {n} string" if n == 1 else f"Copied {n} strings")
