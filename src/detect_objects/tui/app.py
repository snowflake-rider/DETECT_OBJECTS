"""Top-level Textual application for ODIA."""

from __future__ import annotations

from textual.app import App

from ..device_setup import AudioInput, AudioOutput, Camera, Context
from .device_setup_screen import (
    AudioInputScreen,
    AudioOutputScreen,
    CameraScreen,
    SetupSession,
    SummaryScreen,
    WelcomeScreen,
)


class OdiaApp(App[Context | None]):
    """Coordinate the sequential device-setup wizard."""

    TITLE = "ODIA"
    SUB_TITLE = "Object detection and voice control"

    CSS = """
    Screen {
        align: center middle;
        background: $surface;
    }

    .wizard-card {
        width: 86;
        max-width: 100%;
        height: auto;
        max-height: 100%;
        padding: 2 4;
        border: tall $accent;
        background: $panel;
    }

    .welcome-card {
        width: 92;
        text-align: center;
    }

    .brand {
        width: 100%;
        color: $accent;
        text-style: bold;
        text-align: center;
    }

    .hero-title {
        width: 100%;
        margin-top: 1;
        text-style: bold;
        text-align: center;
        color: $text;
    }

    .hero-copy, .hero-note {
        width: 100%;
        text-align: center;
        margin-top: 1;
        color: $text-muted;
    }

    .hero-note {
        margin-top: 0;
        color: $accent;
    }

    .feature-grid, .summary-grid {
        width: 100%;
        height: auto;
        margin: 2 0;
    }

    .feature, .summary-device {
        width: 1fr;
        height: auto;
        margin: 0 1;
        padding: 1 2;
        border: round $primary;
        background: $boost;
        text-align: center;
    }

    .step-rail {
        width: 100%;
        text-align: center;
        margin-bottom: 2;
    }

    .eyebrow, .summary-label {
        color: $accent;
        text-style: bold;
    }

    .wizard-title {
        width: 100%;
        margin-top: 1;
        text-style: bold;
        color: $text;
    }

    .wizard-copy {
        width: 100%;
        margin: 0 0 1 0;
        color: $text-muted;
    }

    .device-badge, .camera-instructions {
        width: 100%;
        height: auto;
        margin: 1 0;
        padding: 1 2;
        border-left: thick $accent;
        background: $boost;
    }

    .field-label {
        margin-top: 1;
        color: $text-muted;
    }

    Select {
        width: 100%;
        margin-bottom: 2;
    }

    .action-row {
        width: 100%;
        height: auto;
        margin-top: 1;
    }

    .action-row Button {
        width: 1fr;
        min-width: 0;
        margin: 0 1;
    }

    .primary-action {
        width: 100%;
        margin-top: 2;
    }

    .confirmation {
        width: 100%;
        margin-top: 1;
        padding: 1 2;
        background: $boost;
    }

    .status {
        width: 100%;
        height: auto;
        margin-top: 1;
        text-align: center;
        color: $text-muted;
    }

    #input-level {
        width: 100%;
        margin-top: 1;
    }

    .summary-card {
        width: 100;
        text-align: center;
    }

    .success-mark {
        width: 100%;
        text-align: center;
        color: $success;
        text-style: bold;
    }

    .summary-title {
        text-align: center;
    }

    .summary-name {
        width: 100%;
        min-height: 2;
        margin-top: 1;
        text-style: bold;
        text-align: center;
    }

    .summary-detail {
        width: 100%;
        color: $text-muted;
        text-align: center;
    }

    .verified {
        width: 100%;
        margin-top: 1;
        color: $success;
        text-align: center;
    }
    """

    BINDINGS = [("q", "quit", "Quit")]

    def __init__(self) -> None:
        super().__init__()
        self.session = SetupSession()

    def on_mount(self) -> None:
        """Open the welcome page as the first wizard screen."""
        self.push_screen(WelcomeScreen(), self._welcome_finished)

    def _welcome_finished(self, started: bool) -> None:
        if started:
            self.push_screen(AudioOutputScreen(), self._audio_output_finished)

    def _audio_output_finished(self, audio_output: AudioOutput) -> None:
        self.session.audio_output = audio_output
        self.push_screen(
            AudioInputScreen(audio_output),
            self._audio_input_finished,
        )

    def _audio_input_finished(self, audio_input: AudioInput) -> None:
        self.session.audio_input = audio_input
        self.push_screen(CameraScreen(), self._camera_finished)

    def _camera_finished(self, camera: Camera) -> None:
        self.session.camera = camera
        self.push_screen(SummaryScreen(self.session), self.finish_device_setup)

    def finish_device_setup(self, context: Context) -> None:
        """Return the confirmed runtime context after the summary page."""
        self.exit(context)


def run_app() -> Context | None:
    """Run the Textual shell and return its selected runtime context."""
    return OdiaApp().run()


def main() -> int:
    """Run the current Textual application."""
    context = run_app()
    if context is None:
        return 1

    print(f"Camera: {context.camera.info.name}")
    print(f"Audio input: {context.audio_input.info.name}")
    print(f"Audio output: {context.audio_output.info.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
