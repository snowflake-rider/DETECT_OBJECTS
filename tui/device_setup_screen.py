"""Textual screen for selecting camera and audio devices."""

from __future__ import annotations

from threading import Event

from textual import on, work
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.message import Message
from textual.screen import Screen
from textual.widgets import (
    Button,
    Footer,
    Header,
    Label,
    ProgressBar,
    Select,
    Static,
)

from device_setup import (
    AudioInput,
    AudioInputInfo,
    AudioOutput,
    AudioOutputInfo,
    Camera,
    CameraInfo,
    CameraProbeResult,
    Context,
    Environment,
    probe_camera,
)
from audio_preview.microphone_preview import (
    AudioPreviewResult,
    monitor_record_and_play,
)
from opencv_preview.camera_preview import (
    CameraPreviewMode,
    CameraPreviewResult,
    launch_camera_preview,
)


class DeviceSetupScreen(Screen[Context]):
    """Collect camera and audio devices without blocking terminal prompts."""

    class CameraProbeFinished(Message):
        """Carry a background camera probe result back to the UI thread."""

        def __init__(self, result: CameraProbeResult) -> None:
            self.result = result
            super().__init__()

    class CameraPreviewFinished(Message):
        """Carry a completed OpenCV preview result back to the UI thread."""

        def __init__(
            self,
            mode: CameraPreviewMode,
            result: CameraPreviewResult,
        ) -> None:
            self.mode = mode
            self.result = result
            super().__init__()

    class AudioLevelChanged(Message):
        """Carry one live microphone level to the UI thread."""

        def __init__(self, decibels: float) -> None:
            self.decibels = decibels
            super().__init__()

    class AudioMonitorFinished(Message):
        """Carry the final live-monitor result to the UI thread."""

        def __init__(self, result: AudioPreviewResult) -> None:
            self.result = result
            super().__init__()

    def __init__(self) -> None:
        super().__init__()
        self.cameras: dict[int, CameraInfo] = {}
        self.audio_inputs: dict[int, AudioInputInfo] = {}
        self.audio_outputs: dict[int, AudioOutputInfo] = {}
        self._camera_action_running = False
        self._audio_action_running = False
        self._audio_monitoring = False
        self._audio_monitor_stop: Event | None = None

    def compose(self) -> ComposeResult:
        """Create the device selectors and confirmation control."""
        yield Header()
        with Container(id="setup-panel"):
            with Horizontal(id="device-columns"):
                with Vertical(classes="device-panel"):
                    yield Label("Camera", classes="field-label")
                    yield Select[int](
                        [],
                        prompt="Select a camera",
                        allow_blank=True,
                        id="camera",
                    )
                    with Horizontal(id="camera-actions", classes="device-actions"):
                        yield Button(
                            "Check",
                            id="test-camera",
                            disabled=True,
                        )
                        yield Button(
                            "Snapshot",
                            id="snapshot-camera",
                            disabled=True,
                        )
                        yield Button(
                            "Stream",
                            id="stream-camera",
                            disabled=True,
                        )

                with Vertical(classes="device-panel"):
                    yield Label("Audio Input", classes="field-label")
                    yield Select[int](
                        [],
                        prompt="Select an input",
                        allow_blank=True,
                        id="audio-input",
                    )
                    with Horizontal(id="audio-actions", classes="device-actions"):
                        yield Button(
                            "Monitor",
                            id="monitor-microphone",
                            disabled=True,
                        )

                with Vertical(classes="device-panel"):
                    yield Label("Audio Output", classes="field-label")
                    yield Select[int](
                        [],
                        prompt="Select an output",
                        allow_blank=True,
                        id="audio-output",
                    )

            yield Button(
                "Continue",
                id="continue",
                variant="success",
                disabled=True,
            )
            yield Static("Finding devices...", id="status")
            microphone_level = ProgressBar(
                total=60,
                show_percentage=False,
                show_eta=False,
                id="microphone-level",
            )
            microphone_level.display = False
            yield microphone_level
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
            audio_inputs = AudioInput.list_devices()
        except Exception as error:
            audio_inputs = []
            errors.append(f"Audio input discovery failed: {error}")

        try:
            audio_outputs = AudioOutput.list_devices()
        except Exception as error:
            audio_outputs = []
            errors.append(f"Audio output discovery failed: {error}")

        self.cameras = {camera.index: camera for camera in cameras}
        self.audio_inputs = {
            audio_input.index: audio_input for audio_input in audio_inputs
        }
        self.audio_outputs = {
            audio_output.index: audio_output for audio_output in audio_outputs
        }
        self.query_one("#camera", Select).set_options(
            (camera.name, camera.index) for camera in cameras
        )
        self.query_one("#audio-input", Select).set_options(
            (audio_input.name, audio_input.index) for audio_input in audio_inputs
        )
        self.query_one("#audio-output", Select).set_options(
            (audio_output.name, audio_output.index) for audio_output in audio_outputs
        )

        status = self.query_one("#status", Static)
        if errors:
            status.update("\n".join(errors))
        elif not cameras or not audio_inputs or not audio_outputs:
            missing = []
            if not cameras:
                missing.append("camera")
            if not audio_inputs:
                missing.append("audio input")
            if not audio_outputs:
                missing.append("audio output")
            status.update(f"No {' or '.join(missing)} found.")
        else:
            status.update("Select a camera, audio input, and audio output to continue.")
        self._update_action_buttons()

    @on(Select.Changed)
    def enable_continue_when_ready(self) -> None:
        """Update available actions when either device selection changes."""
        self._update_action_buttons()

    def _update_action_buttons(self) -> None:
        """Reflect device selections and camera-action state in the controls."""
        camera = self.query_one("#camera", Select)
        audio_input = self.query_one("#audio-input", Select)
        audio_output = self.query_one("#audio-output", Select)
        any_action_running = self._camera_action_running or self._audio_action_running
        camera.disabled = any_action_running
        audio_input.disabled = any_action_running
        audio_output.disabled = any_action_running

        camera_action_disabled = camera.selection is None or any_action_running
        for button_id in ("#test-camera", "#snapshot-camera", "#stream-camera"):
            self.query_one(button_id, Button).disabled = camera_action_disabled

        audio_action_disabled = (
            audio_input.selection is None
            or audio_output.selection is None
            or any_action_running
        )
        monitor_button = self.query_one("#monitor-microphone", Button)
        monitor_button.label = "Done" if self._audio_monitoring else "Monitor"
        monitor_button.disabled = (
            False if self._audio_monitoring else audio_action_disabled
        )

        self.query_one("#continue", Button).disabled = (
            camera.selection is None
            or audio_input.selection is None
            or audio_output.selection is None
            or any_action_running
        )

    @on(Button.Pressed, "#test-camera")
    def test_selected_camera(self) -> None:
        """Start a non-blocking health check for the selected camera."""
        camera_index = self.query_one("#camera", Select).selection
        if camera_index is None:
            return

        self._camera_action_running = True
        self._update_action_buttons()
        self.query_one("#status", Static).update("Testing camera...")
        self.run_camera_probe(Camera(self.cameras[camera_index]))

    @work(thread=True, exclusive=True, group="camera-action")
    def run_camera_probe(self, camera: Camera) -> None:
        """Probe the camera without blocking Textual's event loop."""
        self.post_message(self.CameraProbeFinished(probe_camera(camera)))

    @on(CameraProbeFinished)
    def show_camera_probe_result(self, message: CameraProbeFinished) -> None:
        """Display the completed health check and restore the controls."""
        self._camera_action_running = False
        self._update_action_buttons()

        result = message.result
        if result.available:
            resolution = f"{result.width}×{result.height}"
            fps = f", {result.fps:.1f} FPS" if result.fps is not None else ""
            status = f"Camera test passed: {resolution}{fps}"
        else:
            status = f"Camera test failed: {result.error}"
        self.query_one("#status", Static).update(status)

    @on(Button.Pressed, "#snapshot-camera")
    def show_snapshot_preview(self) -> None:
        """Open a still frame in a dedicated OpenCV window."""
        self._start_camera_preview(CameraPreviewMode.SNAPSHOT)

    @on(Button.Pressed, "#stream-camera")
    def show_stream_preview(self) -> None:
        """Open a live stream in a dedicated OpenCV window."""
        self._start_camera_preview(CameraPreviewMode.STREAM)

    def _start_camera_preview(self, mode: CameraPreviewMode) -> None:
        """Lock setup controls and launch the selected preview mode."""
        camera_index = self.query_one("#camera", Select).selection
        if camera_index is None:
            return

        self._camera_action_running = True
        self._update_action_buttons()
        self.query_one("#status", Static).update(
            f"Opening {mode.value} preview. Press Q or Escape to close it."
        )
        self.run_camera_preview(Camera(self.cameras[camera_index]), mode)

    @work(thread=True, exclusive=True, group="camera-action")
    def run_camera_preview(
        self,
        camera: Camera,
        mode: CameraPreviewMode,
    ) -> None:
        """Wait for the isolated OpenCV preview without blocking Textual."""
        result = launch_camera_preview(camera, mode)
        self.post_message(self.CameraPreviewFinished(mode, result))

    @on(CameraPreviewFinished)
    def show_camera_preview_result(self, message: CameraPreviewFinished) -> None:
        """Restore setup controls after the preview window closes."""
        self._camera_action_running = False
        self._update_action_buttons()

        label = message.mode.value.title()
        if message.result.successful:
            status = f"{label} preview closed."
        else:
            status = f"{label} preview failed: {message.result.error}"
        self.query_one("#status", Static).update(status)

    @on(Button.Pressed, "#monitor-microphone")
    def toggle_microphone_monitor(self) -> None:
        """Start recording or finish it and trigger automatic playback."""
        if self._audio_monitoring:
            self._audio_monitoring = False
            self._update_action_buttons()
            self.query_one("#monitor-microphone", Button).disabled = True
            self.query_one("#status", Static).update(
                "Recording finished. Playing it back..."
            )
            if self._audio_monitor_stop is not None:
                self._audio_monitor_stop.set()
            return

        audio_input_index = self.query_one("#audio-input", Select).selection
        audio_output_index = self.query_one("#audio-output", Select).selection
        if audio_input_index is None or audio_output_index is None:
            return

        stop_event = Event()
        self._audio_monitor_stop = stop_event
        self._audio_action_running = True
        self._audio_monitoring = True
        self._update_action_buttons()
        level_bar = self.query_one("#microphone-level", ProgressBar)
        level_bar.update(progress=0)
        level_bar.display = True
        self.query_one("#status", Static).update('Say "안녕하세요", then choose Done.')
        self.run_audio_monitor(
            AudioInput(self.audio_inputs[audio_input_index]),
            AudioOutput(self.audio_outputs[audio_output_index]),
            stop_event,
        )

    @work(thread=True, exclusive=True, group="audio-action")
    def run_audio_monitor(
        self,
        audio_input: AudioInput,
        audio_output: AudioOutput,
        stop_event: Event,
    ) -> None:
        """Monitor, record, and play back without blocking the UI thread."""

        def report_level(decibels: float) -> None:
            self.post_message(self.AudioLevelChanged(decibels))

        result = monitor_record_and_play(
            audio_input,
            audio_output,
            stop_event,
            report_level,
        )
        self.post_message(self.AudioMonitorFinished(result))

    @on(AudioLevelChanged)
    def show_audio_level(self, message: AudioLevelChanged) -> None:
        """Update the progress bar and display the current decibel level."""
        if not self._audio_monitoring:
            return

        progress = min(max(message.decibels + 60, 0.0), 60.0)
        self.query_one("#microphone-level", ProgressBar).update(progress=progress)
        self.query_one("#status", Static).update(
            f'Say "안녕하세요" — {message.decibels:5.1f} dB — choose Done.'
        )

    @on(AudioMonitorFinished)
    def finish_audio_monitor(self, message: AudioMonitorFinished) -> None:
        """Restore controls after recording and playback finish."""
        self._audio_action_running = False
        self._audio_monitoring = False
        self._audio_monitor_stop = None
        self._update_action_buttons()
        self.query_one("#microphone-level", ProgressBar).display = False

        if message.result.successful:
            status = (
                "Microphone test completed: "
                f"recorded {message.result.duration_seconds:.1f}s, "
                f"peak {message.result.peak_db:.1f} dB."
            )
        else:
            status = f"Microphone test failed: {message.result.error}"
        self.query_one("#status", Static).update(status)

    def on_unmount(self) -> None:
        """Stop a live microphone stream when leaving the setup screen."""
        if self._audio_monitor_stop is not None:
            self._audio_monitor_stop.set()

    @on(Button.Pressed, "#continue")
    def create_context(self) -> None:
        """Create the selected context and dismiss this screen."""
        camera_index = self.query_one("#camera", Select).selection
        audio_input_index = self.query_one("#audio-input", Select).selection
        audio_output_index = self.query_one("#audio-output", Select).selection
        if (
            camera_index is None
            or audio_input_index is None
            or audio_output_index is None
        ):
            self.query_one("#status", Static).update(
                "Select all devices before continuing."
            )
            return

        self.dismiss(
            Context(
                environment=Environment.detect(),
                camera=Camera(self.cameras[camera_index]),
                audio_input=AudioInput(self.audio_inputs[audio_input_index]),
                audio_output=AudioOutput(self.audio_outputs[audio_output_index]),
            )
        )
