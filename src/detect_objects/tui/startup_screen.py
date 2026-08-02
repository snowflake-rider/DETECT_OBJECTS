"""Show simple progress while ODIA prepares its runtime."""

from collections.abc import Callable

from textual import on, work
from textual.app import ComposeResult
from textual.message import Message
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Static
from textual.containers import VerticalScroll

from ..runtime import STARTUP_STEPS, StartupReporter, StartupUpdate

StartupTask = Callable[[StartupReporter], None]

STEP_LABELS = {
    "classes": "Class names",
    "voice": "Voice model",
    "microphone": "Microphone",
    "camera": "Camera",
    "vision": "Vision model",
}


class StartupScreen(Screen[bool]):
    """Display updates from runtime preparation without knowing its details."""

    class UpdateReceived(Message):
        def __init__(self, update: StartupUpdate) -> None:
            self.update = update
            super().__init__()

    class PreparationFinished(Message):
        pass

    class PreparationFailed(Message):
        def __init__(self, error: Exception) -> None:
            self.error = error
            super().__init__()

    def __init__(self, startup_task: StartupTask) -> None:
        super().__init__()
        self.startup_task = startup_task
        self.successful = False

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(classes="wizard-card startup-card"):
            yield Static("STARTING ODIA", classes="eyebrow")
            yield Static("Preparing your models", classes="wizard-title")
            yield Static(
                "This can take a moment the first time.",
                classes="wizard-copy",
            )
            for step in STARTUP_STEPS:
                yield Static(
                    f"○  {STEP_LABELS[step]}",
                    id=f"startup-{step}",
                    classes="startup-step",
                )
            yield Static("Starting…", id="startup-status", classes="status")
            yield Button(
                "Please wait…",
                id="finish-startup",
                variant="success",
                disabled=True,
                classes="primary-action",
            )
        yield Footer()

    def on_mount(self) -> None:
        self.prepare_runtime()

    @work(thread=True, exclusive=True, group="runtime-startup")
    def prepare_runtime(self) -> None:
        try:
            self.startup_task(self._report)
        except Exception as error:
            self.post_message(self.PreparationFailed(error))
            return
        self.post_message(self.PreparationFinished())

    def _report(self, update: StartupUpdate) -> None:
        self.post_message(self.UpdateReceived(update))

    @on(UpdateReceived)
    def show_update(self, message: UpdateReceived) -> None:
        update = message.update
        if update.step not in STARTUP_STEPS:
            raise ValueError(f"Unknown startup step: {update.step}")

        marker = "[green]✓[/]" if update.finished else "[cyan]●[/]"
        self.query_one(f"#startup-{update.step}", Static).update(
            f"{marker}  {update.message}"
        )
        self.query_one("#startup-status", Static).update(update.message)

    @on(PreparationFinished)
    def preparation_finished(self) -> None:
        self.successful = True
        self.query_one("#startup-status", Static).update(
            "Everything is ready. Open the camera to begin."
        )
        button = self.query_one("#finish-startup", Button)
        button.label = "Open Camera  →"
        button.disabled = False

    @on(PreparationFailed)
    def preparation_failed(self, message: PreparationFailed) -> None:
        self.query_one("#startup-status", Static).update(
            f"[red]Startup failed:[/] {message.error}"
        )
        button = self.query_one("#finish-startup", Button)
        button.label = "Close"
        button.variant = "error"
        button.disabled = False

    @on(Button.Pressed, "#finish-startup")
    def finish_startup(self) -> None:
        self.dismiss(self.successful)
