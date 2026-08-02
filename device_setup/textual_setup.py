"""Select the camera and microphone for one run in a Textual interface."""

from __future__ import annotations

from cv2_enumerate_cameras.camera_info import CameraInfo
from textual import on
from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Button, Footer, Header, Label, Select, Static

from .audio import Audio, AudioInfo
from .camera import Camera
from .context import Context
from .environment import Environment


class DeviceSetupApp(App[Context | None]):
    """Collect a camera and microphone without blocking terminal prompts."""

    TITLE = "ODIA Device Setup"
    SUB_TITLE = "Choose the devices to use for this run"

    CSS = """
    Screen {
        align: center middle;
    }

    #setup-panel {
        width: 64;
        height: auto;
        padding: 1 2;
        border: round $accent;
        background: $panel;
    }

    .field-label {
        margin-top: 1;
    }

    Select {
        width: 100%;
        margin-bottom: 1;
    }

    #continue {
        width: 100%;
        margin-top: 1;
    }

    #status {
        height: auto;
        margin-top: 1;
        text-align: center;
    }
    """

    BINDINGS = [("q", "quit", "Quit")]

    def __init__(self) -> None:
        super().__init__()
        self.cameras: dict[int, CameraInfo] = {}
        self.microphones: dict[int, AudioInfo] = {}

    def compose(self) -> ComposeResult:
        """Create the device selectors and confirmation control."""
        yield Header()

        with Container(id="setup-panel"):
            yield Label("Camera", classes="field-label")
            yield Select[int](
                [],
                prompt="Select a camera",
                allow_blank=True,
                id="camera",
            )

            yield Label("Microphone", classes="field-label")
            yield Select[int](
                [],
                prompt="Select a microphone",
                allow_blank=True,
                id="microphone",
            )

            yield Button(
                "Continue",
                id="continue",
                variant="success",
                disabled=True,
            )
            yield Static("Finding devices...", id="status")

        yield Footer()

    def on_mount(self) -> None:
        """Discover devices and populate both selectors."""
        errors: list[str] = []

        try:
            cameras = Camera.list_devices()
        except Exception as error:
            cameras = []
            errors.append(f"Camera discovery failed: {error}")

        try:
            microphones = Audio.list_devices()
        except Exception as error:
            microphones = []
            errors.append(f"Microphone discovery failed: {error}")

        self.cameras = {camera.index: camera for camera in cameras}
        self.microphones = {microphone.index: microphone for microphone in microphones}

        self.query_one("#camera", Select).set_options(
            (camera.name, camera.index) for camera in cameras
        )
        self.query_one("#microphone", Select).set_options(
            (microphone.name, microphone.index) for microphone in microphones
        )

        status = self.query_one("#status", Static)
        if errors:
            status.update("\n".join(errors))
        elif not cameras or not microphones:
            missing = []
            if not cameras:
                missing.append("camera")
            if not microphones:
                missing.append("microphone")
            status.update(f"No {' or '.join(missing)} found.")
        else:
            status.update("Select a camera and microphone to continue.")

    @on(Select.Changed)
    def enable_continue_when_ready(self) -> None:
        """Enable Continue only when both device selections are present."""
        camera = self.query_one("#camera", Select)
        microphone = self.query_one("#microphone", Select)
        self.query_one("#continue", Button).disabled = (
            camera.selection is None or microphone.selection is None
        )

    @on(Button.Pressed, "#continue")
    def create_context(self) -> None:
        """Create and return the context selected by the user."""
        camera_index = self.query_one("#camera", Select).selection
        microphone_index = self.query_one("#microphone", Select).selection

        if camera_index is None or microphone_index is None:
            self.query_one("#status", Static).update(
                "Select both devices before continuing."
            )
            return

        context = Context(
            environment=Environment.detect(),
            camera=Camera(self.cameras[camera_index]),
            audio=Audio(self.microphones[microphone_index]),
        )
        self.exit(context)


def run_setup() -> Context | None:
    """Run the Textual device setup and return the completed context."""
    return DeviceSetupApp().run()


def main() -> int:
    """Run device setup as a standalone application."""
    context = run_setup()
    if context is None:
        return 1

    print(f"Camera: {context.camera.info.name}")
    print(f"Microphone: {context.audio.info.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
