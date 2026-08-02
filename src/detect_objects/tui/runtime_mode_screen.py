"""Choose the interface used after the setup wizard."""

from textual import on
from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, RadioButton, RadioSet, Static

from ..launch_mode import RuntimeMode


class RuntimeModeScreen(Screen[RuntimeMode]):
    """Offer the new desktop preview without replacing the stable runtime."""

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(classes="wizard-card"):
            yield Static("RUNTIME INTERFACE", classes="eyebrow")
            yield Static("How should ODIA open?", classes="wizard-title")
            yield Static(
                "Choose the new integrated desktop preview or keep using the "
                "current stable runtime.",
                classes="wizard-copy",
            )
            yield Static(
                "[bold $accent]Desktop Dashboard (Preview)[/] — PySide6 integrated "
                "window for video, status, transcripts, and typed commands.",
                classes="device-badge",
            )
            yield Static(
                "[bold $accent]Classic Runtime (Stable)[/] — Terminal output with "
                "a native OpenCV camera preview.",
                classes="device-badge",
            )
            with RadioSet(id="runtime-mode", classes="runtime-mode-set"):
                yield RadioButton(
                    "Desktop Dashboard (Preview)",
                    id="mode-desktop",
                    classes="runtime-mode-choice",
                )
                yield RadioButton(
                    "Classic Runtime (Stable)",
                    value=True,
                    id="mode-classic",
                    classes="runtime-mode-choice",
                )
            yield Button(
                "Launch ODIA  →",
                id="launch-runtime",
                variant="success",
                classes="primary-action",
            )
        yield Footer()

    @on(Button.Pressed, "#launch-runtime")
    def launch_runtime(self) -> None:
        selected = self.query_one("#runtime-mode", RadioSet).pressed_button
        if selected is None:
            return
        mode = (
            RuntimeMode.DESKTOP
            if selected.id == "mode-desktop"
            else RuntimeMode.CLASSIC
        )
        self.dismiss(mode)
