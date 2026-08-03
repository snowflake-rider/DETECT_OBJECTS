"""Top-level Textual application for ODIA."""

from __future__ import annotations

from dataclasses import replace

from textual.app import App

from ..device_setup import AudioInput, AudioOutput, Camera, Context
from ..launch_mode import RuntimeMode
from ..models import ModelSelection
from ..ui_theme import DEFAULT_UI_THEME, UI_THEME_NAMES
from .device_setup_screen import (
    AudioInputScreen,
    AudioOutputScreen,
    CameraScreen,
    ModelSelectionScreen,
    SetupSession,
    SummaryScreen,
    WelcomeScreen,
)
from .startup_screen import StartupScreen, StartupTask
from .runtime_mode_screen import RuntimeModeScreen


def _apply_theme(app: App, theme_name: str) -> None:
    """Apply one of the themes offered by the welcome screen."""
    if theme_name not in UI_THEME_NAMES:
        raise ValueError(f"Unknown TUI theme: {theme_name}")
    app.theme = theme_name


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

    .theme-picker {
        width: 100%;
        height: 3;
        margin-top: 1;
        align: center middle;
    }

    .theme-label {
        width: 18;
        color: $text-muted;
        text-align: right;
        padding-right: 2;
    }

    .theme-picker Select {
        width: 1fr;
        margin-bottom: 0;
    }

    .feature-list {
        width: 100%;
        height: auto;
        margin: 1 0;
    }

    .feature-row {
        width: 100%;
        height: 3;
        padding: 0 2;
        border-left: thick $primary;
        background: $boost;
        align: left middle;
    }

    .feature-number {
        width: 8;
        height: 3;
        color: $accent;
        text-align: left;
    }

    .feature-title {
        width: 22;
        height: 1;
        color: $text;
        text-style: bold;
        text-align: left;
    }

    .feature-copy {
        width: 1fr;
        height: auto;
        color: $text-muted;
        text-align: left;
    }

    .summary-table {
        width: 100%;
        height: auto;
        margin: 2 0;
        border: round $primary;
        background: $boost;
    }

    .summary-table-header, .summary-table-row {
        width: 100%;
        height: 3;
        padding: 1 2 0 2;
        align: left middle;
    }

    .summary-table-header {
        color: $text-muted;
        text-style: bold;
        border-bottom: solid $primary;
    }

    .summary-table-row {
        border-bottom: solid $surface;
    }

    .summary-table-label {
        width: 22;
        color: $accent;
        text-style: bold;
    }

    .summary-table-value {
        width: 1fr;
        color: $text;
        text-style: bold;
    }

    .summary-table-detail {
        width: 24;
        color: $text-muted;
        text-align: right;
    }

    .step-rail {
        width: 100%;
        text-align: center;
        margin-bottom: 2;
    }

    .eyebrow {
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

    .model-description {
        width: 100%;
        height: auto;
        margin: -1 0 1 0;
        color: $text-muted;
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

    .runtime-mode-set {
        width: 100%;
        height: auto;
        margin: 1 0;
        padding: 1 2;
        border: round $primary;
        background: $boost;
    }

    .runtime-mode-choice {
        width: 100%;
        height: 3;
        padding: 0 1;
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

    """

    BINDINGS = [("q", "quit", "Quit")]

    def __init__(self) -> None:
        super().__init__()
        self.session = SetupSession()
        self._completed_context: Context | None = None

    def on_mount(self) -> None:
        """Open the welcome page as the first wizard screen."""
        _apply_theme(self, DEFAULT_UI_THEME)
        self.push_screen(WelcomeScreen(), self._welcome_finished)

    def _welcome_finished(self, started: bool) -> None:
        if started:
            self.push_screen(
                AudioOutputScreen(self.session.audio_output),
                self._audio_output_finished,
            )

    def _audio_output_finished(self, audio_output: AudioOutput | None) -> None:
        if audio_output is None:
            self.push_screen(WelcomeScreen(), self._welcome_finished)
            return
        self.session.audio_output = audio_output
        self.push_screen(
            AudioInputScreen(audio_output, self.session.audio_input),
            self._audio_input_finished,
        )

    def _audio_input_finished(self, audio_input: AudioInput | None) -> None:
        if audio_input is None:
            self.push_screen(
                AudioOutputScreen(self.session.audio_output),
                self._audio_output_finished,
            )
            return
        self.session.audio_input = audio_input
        self.push_screen(
            CameraScreen(self.session.camera),
            self._camera_finished,
        )

    def _camera_finished(self, camera: Camera | None) -> None:
        if camera is None:
            if self.session.audio_output is None:
                raise RuntimeError("Audio output is required before camera setup.")
            self.push_screen(
                AudioInputScreen(
                    self.session.audio_output,
                    self.session.audio_input,
                ),
                self._audio_input_finished,
            )
            return
        self.session.camera = camera
        self.push_screen(
            ModelSelectionScreen(self.session.models),
            self._models_finished,
        )

    def _models_finished(self, models: ModelSelection | None) -> None:
        if models is None:
            self.push_screen(
                CameraScreen(self.session.camera),
                self._camera_finished,
            )
            return
        self.session.models = models
        self.push_screen(SummaryScreen(self.session), self.finish_device_setup)

    def finish_device_setup(self, context: Context | None) -> None:
        """Ask how to launch after every device and model is confirmed."""
        if context is None:
            self.push_screen(
                ModelSelectionScreen(self.session.models),
                self._models_finished,
            )
            return
        self._completed_context = context
        self.push_screen(RuntimeModeScreen(), self._runtime_mode_finished)

    def _runtime_mode_finished(self, runtime_mode: RuntimeMode | None) -> None:
        """Return setup selections with the chosen runtime interface."""
        if runtime_mode is None:
            self.push_screen(SummaryScreen(self.session), self.finish_device_setup)
            return
        if self._completed_context is None:
            raise RuntimeError("Runtime mode was selected before setup completed.")
        self.exit(
            replace(
                self._completed_context,
                ui_theme=self.theme,
                runtime_mode=runtime_mode,
            )
        )


class StartupApp(App[bool | None]):
    """Keep the TUI open while the selected models are prepared."""

    CSS = OdiaApp.CSS + """
    .startup-card {
        width: 76;
    }

    .startup-step {
        height: 2;
        padding: 0 2;
    }
    """

    BINDINGS = [("q", "quit", "Quit")]

    def __init__(
        self,
        startup_task: StartupTask,
        theme_name: str = DEFAULT_UI_THEME,
    ) -> None:
        super().__init__()
        self.startup_task = startup_task
        self.theme_name = theme_name

    def on_mount(self) -> None:
        _apply_theme(self, self.theme_name)
        self.push_screen(StartupScreen(self.startup_task), self.exit)


def run_app() -> Context | None:
    """Run the Textual shell and return its selected runtime context."""
    return OdiaApp().run()


def run_startup_app(
    startup_task: StartupTask,
    theme_name: str = DEFAULT_UI_THEME,
) -> bool:
    """Show runtime preparation and return whether startup succeeded."""
    return StartupApp(startup_task, theme_name).run() is True


def main() -> int:
    """Run the current Textual application."""
    context = run_app()
    if context is None:
        return 1

    print(f"Camera: {context.camera.info.name}")
    print(f"Audio input: {context.audio_input.info.name}")
    print(f"Audio output: {context.audio_output.info.name}")
    print(f"Vision model: {context.models.vision_id}")
    print(f"Voice model: {context.models.voice_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
