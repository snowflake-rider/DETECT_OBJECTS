"""Textual screen for selecting camera and microphone input devices."""

from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, Select, Static

from device_setup import Audio, AudioInfo, Camera, CameraInfo, Context, Environment


class DeviceSetupScreen(Screen[Context]):
    """Collect a camera and microphone without blocking terminal prompts."""

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
        """Create the selected context and dismiss this screen."""
        camera_index = self.query_one("#camera", Select).selection
        microphone_index = self.query_one("#microphone", Select).selection
        if camera_index is None or microphone_index is None:
            self.query_one("#status", Static).update(
                "Select both devices before continuing."
            )
            return

        self.dismiss(
            Context(
                environment=Environment.detect(),
                camera=Camera(self.cameras[camera_index]),
                audio=Audio(self.microphones[microphone_index]),
            )
        )
