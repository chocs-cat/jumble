"""The interactive generator (docs/spec.md §7): controls beside results, live validation."""

import contextlib
import os
import time
from importlib.metadata import version
from pathlib import Path
from typing import ClassVar

from textual.app import App, ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Grid, Horizontal, Vertical, VerticalScroll
from textual.dom import DOMNode
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import (
    Button,
    Checkbox,
    Footer,
    Header,
    Input,
    OptionList,
    SelectionList,
    Static,
)
from textual.widgets.option_list import Option

from jumble.config import config_path, file_settings, load, save
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


def parse_int(value: str) -> int:
    """An integer input's value; one that doesn't parse (empty, `-`) counts as 0 (§7.1)."""
    try:
        return int(value)
    except ValueError:
        return 0


def titled(widget: Widget, title: str) -> Widget:
    """`widget`, labelled in its border."""
    widget.border_title = title
    return widget


def controls(start: Settings) -> list[Widget]:
    """The controls of §7.1, holding `start` as given: the main screen's pane and
    the settings screen's form are both built here, so they match (§7.4)."""
    return [
        Horizontal(
            titled(Input(str(start.length), id="length", type="integer"), "Length"),
            titled(Input(str(start.count), id="count", type="integer"), "Count"),
            id="numbers",
        ),
        titled(
            SelectionList[str](
                *((name, name, name in start.charsets) for name in CHARSETS), id="charsets"
            ),
            "Sets",
        ),
        titled(Input(start.custom, id="custom"), "Custom"),
        Grid(
            *(Checkbox(label, getattr(start, setting), id=wid) for wid, label, setting in OPTIONS),
            id="options",
        ),
    ]


def read_controls(node: DOMNode) -> Settings:
    """The controls under `node` as one `Settings`, unvalidated and with no default
    fill (§7.1); an integer input that doesn't parse counts as 0."""
    selected = set(node.query_one("#charsets", SelectionList).selected)
    options = {setting: node.query_one(f"#{wid}", Checkbox).value for wid, _, setting in OPTIONS}
    return Settings(
        length=parse_int(node.query_one("#length", Input).value),
        count=parse_int(node.query_one("#count", Input).value),
        charsets=tuple(name for name in CHARSETS if name in selected),
        custom=node.query_one("#custom", Input).value,
        **options,
    )


def set_controls(node: DOMNode, settings: Settings) -> None:
    """Set the controls under `node` to `settings`, as `controls` builds them."""
    node.query_one("#length", Input).value = str(settings.length)
    node.query_one("#count", Input).value = str(settings.count)
    sets = node.query_one("#charsets", SelectionList)
    sets.deselect_all()
    for name in settings.charsets:
        sets.select(name)
    node.query_one("#custom", Input).value = settings.custom
    for wid, _, setting in OPTIONS:
        node.query_one(f"#{wid}", Checkbox).value = getattr(settings, setting)


class SettingsScreen(ModalScreen[tuple[Settings, Path] | None]):
    """The settings file as a form: `,` opens it (§7.4, DEC-20).

    It holds the main screen's controls, filled with `start`, and the file's
    `path` as it resolved on opening. Save validates the form as the banner
    does and writes the file, closing with the settings and the path it
    saved to; Cancel and `escape` close with None. The form's messages stop
    here, so nothing in it reaches the main screen's handlers.
    """

    # The form's only key: the main screen's don't act while it is open (DEC-20).
    BINDINGS: ClassVar[list[BindingType]] = [Binding("escape", "cancel", show=False)]
    # The first control. Left unset, the screen takes the App's "#results",
    # which it lacks, and nothing has focus.
    AUTO_FOCUS = "#length"

    def __init__(self, start: Settings, path: Path) -> None:
        super().__init__()
        self.start = start
        self.path = path

    def compose(self) -> ComposeResult:
        # The dialog scrolls as a whole when the terminal is too short for it.
        with VerticalScroll(id="dialog") as dialog:
            dialog.border_title = "Settings"
            # A path can hold `[`, so it is shown as text, not markup.
            yield Static(str(self.path), id="path", markup=False)
            with Vertical(id="form"):
                yield from controls(self.start)
            with Horizontal(id="buttons"):
                yield Button("Save", id="save", variant="primary")
                yield Button("Cancel", id="cancel")

    # The App's handlers would check the main screen's controls, and `enter`
    # would jumble there (§7.2): the form's messages go no further than here.

    def on_input_changed(self, event: Input.Changed) -> None:
        event.stop()

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        event.stop()

    def on_selection_list_selected_changed(self, event: SelectionList.SelectedChanged) -> None:
        event.stop()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        # `enter` in a form input saves, as the Save button does (§7.4).
        event.stop()
        self.action_save()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        if event.button.id == "save":
            self.action_save()
        else:
            self.action_cancel()

    def action_save(self) -> None:
        """Validate the form, write the file, and close with what was saved (§7.4)."""
        settings = read_controls(self)
        try:
            # The banner's check, so the form and the main screen agree (§7.1, DEC-20).
            strength(settings)
        except JumbleError as e:
            self.app.notify(str(e), severity="error")
            return
        # Resolved now, not on opening (§7.4).
        path = config_path()
        try:
            save(path, settings)
        except JumbleError as e:
            # `save`'s own failure: the screen stays open, the main screen as it was.
            self.app.notify(str(e), severity="error")
            return
        self.dismiss((settings, path))

    def action_cancel(self) -> None:
        self.dismiss(None)


class JumbleApp(App[None]):
    # The results pane holds focus so letter keys reach the bindings (DEC-12).
    AUTO_FOCUS = "#results"
    CSS = """
    #error { display: none; background: $error; color: $text; padding: 0 1; }
    #error.shown { display: block; }
    #controls { width: 50; border-right: solid $panel; }
    SettingsScreen { align: center middle; }
    #dialog { width: 58; height: auto; max-height: 100%; border: thick $primary; padding: 0 1; }
    #form { height: auto; }
    #path { color: $text-muted; }
    #buttons { height: auto; align-horizontal: right; }
    #buttons Button { margin-left: 1; }
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
        ("s", "save", "Save"),
        ("d", "save_defaults", "Save defaults"),
        ("comma", "settings", "Settings"),
        ("q", "quit", "Quit"),
        Binding("escape", "focus_results", show=False),
    ]

    def __init__(self, settings: Settings = DEFAULTS, file_error: str | None = None) -> None:
        """`settings` are the controls' starting values, as given: the caller fills
        the default sets (§5.2, §7.5, DEC-9). `file_error` is a settings-file
        message to show in an error toast at start (§7.4, DEC-17)."""
        super().__init__()
        self.initial = settings
        self.file_error = file_error
        self.title = f"jumble {version('jumble')}"
        self.strings: list[str] = []
        self.valid = False
        # The banner's §6 message while the controls are invalid (§7.1).
        self.problem = ""

    def compose(self) -> ComposeResult:
        # The starting values go in here, not in `on_mount`, so the first
        # `check` sees them (§7.5).
        start = self.initial
        yield Header()
        yield Static(id="error")
        with Horizontal():
            with VerticalScroll(id="controls"):
                yield from controls(start)
            # Strings can hold `[`, so they are shown as text, not markup.
            yield OptionList(id="results", markup=False)
        yield Footer()

    def on_mount(self) -> None:
        # An invalid start shows the banner and jumbles nothing (§7.2, §7.5).
        self.check()
        self.action_jumble()
        if self.file_error:
            self.notify(self.file_error, severity="error")

    @property
    def main(self) -> DOMNode:
        """The main screen, under the settings screen while that is open."""
        return self.screen_stack[0]

    def settings(self) -> Settings:
        """The main screen's controls as one `Settings`, unvalidated, no default fill (§7.1)."""
        return read_controls(self.main)

    def check(self) -> None:
        """Validate the controls: set the subtitle, or show the §6 message (§7.1)."""
        error = self.query_one("#error", Static)
        try:
            line = strength_line(strength(self.settings()))
        except JumbleError as e:
            self.valid = False
            self.problem = str(e)
            self.sub_title = ""
            error.update(self.problem)
            error.add_class("shown")
            return
        self.valid = True
        self.problem = ""
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

    # Copying and saving use the last jumble's strings, valid controls or
    # not; before any jumble there is nothing to copy or save (§7.1, §7.2).

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

    def action_save(self) -> None:
        """Write every string to a new `jumble-<epoch>-<count>.txt` here (§7.3, DEC-13)."""
        if not self.strings:
            return
        name = f"jumble-{int(time.time())}-{len(self.strings)}.txt"
        # The same bytes as the command line's lines output (§4.1).
        data = "".join(f"{s}\n" for s in self.strings).encode()
        try:
            # One exclusive create, so an existing file is never replaced (§7.3).
            f = open(name, "xb")  # noqa: SIM115
        except FileExistsError:
            self.notify(f"{name} exists; nothing saved", severity="error")
            return
        except OSError as e:
            self.notify(f"can't save {name}: {e.strerror}", severity="error")
            return
        try:
            with f:
                f.write(data)
        except OSError as e:
            # The exclusive create made this file, so removing it removes only
            # the partial save (§7.3).
            with contextlib.suppress(OSError):
                os.remove(name)
            self.notify(f"can't save {name}: {e.strerror}", severity="error")
            return
        self.notify(f"Saved {name}")

    def action_save_defaults(self) -> None:
        """Save the controls as the settings file's defaults (§7.4, DEC-18)."""
        if not self.valid:
            # Never a file the command line would refuse (§7.4).
            self.notify(self.problem, severity="error")
            return
        # Resolved now, so a TUI started with --no-config saves too (§7.4).
        path = config_path()
        try:
            save(path, self.settings())
        except JumbleError as e:
            self.notify(str(e), severity="error")
            return
        self.notify(f"Saved defaults to {path}")

    def action_settings(self) -> None:
        """Open the settings screen on the settings file (§7.4, DEC-20)."""
        path = config_path()
        try:
            start = file_settings(load(path))
        except JumbleError as e:
            # The built-in defaults, so Save repairs the file (DEC-17).
            start = DEFAULTS
            self.notify(str(e), severity="error")
        self.push_screen(SettingsScreen(start, path), self.saved)

    def saved(self, result: tuple[Settings, Path] | None) -> None:
        """After the settings screen: set the controls to what it saved (§7.4)."""
        if result is None:
            return
        settings, path = result
        set_controls(self.main, settings)
        # Setting a control posts its change for later: check now, so the
        # banner and the subtitle follow before the toast. No jumble (§7.1).
        self.check()
        self.notify(f"Saved defaults to {path}")
