"""Sequential Textual wizard for selecting and verifying runtime devices."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Event

import sounddevice as sd
from textual import on, work
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.screen import Screen
from textual.widgets import (
    Button,
    Checkbox,
    Footer,
    Header,
    Label,
    ProgressBar,
    Select,
    Static,
)

from audio_preview.microphone_preview import (
    AudioRecording,
    PlaybackResult,
    RecordingResult,
    monitor_and_record,
    play_recording,
)
from device_setup import (
    AudioInput,
    AudioInputInfo,
    AudioOutput,
    AudioOutputInfo,
    AudioOutputProbeResult,
    Camera,
    CameraInfo,
    Context,
    Environment,
    probe_audio_output,
)
from opencv_preview.camera_preview import (
    CameraPreviewMode,
    CameraPreviewResult,
    launch_camera_preview,
)


def _step_rail(active: int) -> Static:
    """Build a compact visual indicator for the sequential setup steps."""
    labels = ("OUTPUT", "INPUT", "VIDEO", "READY")
    parts: list[str] = []
    for position, label in enumerate(labels, start=1):
        if position < active:
            parts.append(f"[green]✓ {label}[/]")
        elif position == active:
            parts.append(f"[bold #7dd3fc]● {label}[/]")
        else:
            parts.append(f"[dim]○ {label}[/]")
    return Static("   ───   ".join(parts), classes="step-rail")


@dataclass
class SetupSession:
    """Selections confirmed while the user advances through the wizard."""

    audio_output: AudioOutput | None = None
    audio_input: AudioInput | None = None
    camera: Camera | None = None

    def build_context(self) -> Context:
        """Create the runtime context after every device is confirmed."""
        if self.audio_output is None or self.audio_input is None or self.camera is None:
            raise RuntimeError("Device setup is incomplete.")
        return Context(
            environment=Environment.detect(),
            camera=self.camera,
            audio_input=self.audio_input,
            audio_output=self.audio_output,
        )


class WelcomeScreen(Screen[bool]):
    """Introduce the guided setup before any hardware is accessed."""

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(classes="wizard-card welcome-card"):
            yield Static("ODIA", classes="brand")
            yield Static("DEVICE SETUP", classes="hero-title")
            yield Static(
                "Let’s make sure you can hear, speak, and be seen.",
                classes="hero-copy",
            )
            yield Static(
                "Three quick guided checks · about two minutes",
                classes="hero-note",
            )
            with Horizontal(classes="feature-grid"):
                yield Static(
                    "🔊\n[b]Sound[/b]\nChoose and verify output", classes="feature"
                )
                yield Static(
                    "🎙\n[b]Voice[/b]\nRecord and hear yourself", classes="feature"
                )
                yield Static(
                    "📷\n[b]Video[/b]\nSnapshot and live preview", classes="feature"
                )
            yield Button(
                "Begin Setup  →",
                id="begin-setup",
                variant="primary",
                classes="primary-action",
            )
        yield Footer()

    @on(Button.Pressed, "#begin-setup")
    def begin_setup(self) -> None:
        self.dismiss(True)


class AudioOutputScreen(Screen[AudioOutput]):
    """Select an output, play a cat sample, and collect confirmation."""

    class SampleFinished(Message):
        def __init__(self, result: AudioOutputProbeResult) -> None:
            self.result = result
            super().__init__()

    def __init__(self) -> None:
        super().__init__()
        self.outputs: dict[int, AudioOutputInfo] = {}
        self._busy = False
        self._sample_played = False

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(classes="wizard-card"):
            yield _step_rail(1)
            yield Static("01 / AUDIO OUTPUT", classes="eyebrow")
            yield Static("Where should ODIA play sound?", classes="wizard-title")
            yield Static(
                "Choose an output, then listen for a short cat meow.",
                classes="wizard-copy",
            )
            yield Label("Audio output", classes="field-label")
            yield Select[int](
                [],
                prompt="Choose speakers or headphones",
                allow_blank=True,
                id="audio-output",
            )
            with Horizontal(classes="action-row"):
                yield Button(
                    "▶  Play Cat Meow",
                    id="play-output-sample",
                    disabled=True,
                )
                yield Button(
                    "Next  →",
                    id="next-output",
                    variant="primary",
                    disabled=True,
                )
            yield Checkbox(
                "Yes, I heard the cat from this output",
                id="confirm-output",
                disabled=True,
                classes="confirmation",
            )
            yield Static("Finding audio outputs…", id="output-status", classes="status")
        yield Footer()

    def on_mount(self) -> None:
        try:
            outputs = AudioOutput.list_devices()
        except (RuntimeError, sd.PortAudioError) as error:
            outputs = []
            self.query_one("#output-status", Static).update(
                f"Audio output discovery failed: {error}"
            )

        self.outputs = {output.index: output for output in outputs}
        self.query_one("#audio-output", Select).set_options(
            (output.name, output.index) for output in outputs
        )
        if outputs:
            self.query_one("#output-status", Static).update(
                "Select an output to enable the sample."
            )
        else:
            self.query_one("#output-status", Static).update(
                "No audio outputs were found."
            )

    @on(Select.Changed, "#audio-output")
    def output_changed(self) -> None:
        self._sample_played = False
        confirmation = self.query_one("#confirm-output", Checkbox)
        confirmation.value = False
        confirmation.disabled = True
        selection = self.query_one("#audio-output", Select).selection
        self.query_one("#play-output-sample", Button).disabled = (
            selection is None or self._busy
        )
        self.query_one("#next-output", Button).disabled = True
        if selection is not None:
            self.query_one("#output-status", Static).update(
                "Ready to play the cat sample."
            )

    @on(Button.Pressed, "#play-output-sample")
    def play_sample(self) -> None:
        output_index = self.query_one("#audio-output", Select).selection
        if output_index is None:
            return
        self._busy = True
        self.query_one("#audio-output", Select).disabled = True
        self.query_one("#play-output-sample", Button).disabled = True
        self.query_one("#output-status", Static).update("Playing cat meow…")
        self.run_output_sample(AudioOutput(self.outputs[output_index]))

    @work(thread=True, exclusive=True, group="output-sample")
    def run_output_sample(self, output: AudioOutput) -> None:
        self.post_message(self.SampleFinished(probe_audio_output(output)))

    @on(SampleFinished)
    def sample_finished(self, message: SampleFinished) -> None:
        self._busy = False
        self.query_one("#audio-output", Select).disabled = False
        self.query_one("#play-output-sample", Button).disabled = False
        if message.result.available:
            self._sample_played = True
            self.query_one("#confirm-output", Checkbox).disabled = False
            self.query_one("#output-status", Static).update(
                "Sample finished. Did you hear the cat?"
            )
        else:
            self.query_one("#output-status", Static).update(
                f"Output test failed: {message.result.error}"
            )

    @on(Checkbox.Changed, "#confirm-output")
    def output_confirmation_changed(self) -> None:
        confirmed = self.query_one("#confirm-output", Checkbox).value
        self.query_one("#next-output", Button).disabled = not (
            self._sample_played and confirmed
        )

    @on(Button.Pressed, "#next-output")
    def finish_output(self) -> None:
        output_index = self.query_one("#audio-output", Select).selection
        if output_index is not None:
            self.dismiss(AudioOutput(self.outputs[output_index]))


class AudioInputScreen(Screen[AudioInput]):
    """Record an input, play it back, and collect confirmation."""

    class LevelChanged(Message):
        def __init__(self, decibels: float) -> None:
            self.decibels = decibels
            super().__init__()

    class RecordingFinished(Message):
        def __init__(self, result: RecordingResult) -> None:
            self.result = result
            super().__init__()

    class PlaybackFinished(Message):
        def __init__(self, result: PlaybackResult) -> None:
            self.result = result
            super().__init__()

    def __init__(self, audio_output: AudioOutput) -> None:
        super().__init__()
        self.audio_output = audio_output
        self.inputs: dict[int, AudioInputInfo] = {}
        self._monitoring = False
        self._busy = False
        self._stop_event: Event | None = None
        self._recording: AudioRecording | None = None
        self._playback_succeeded = False

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(classes="wizard-card"):
            yield _step_rail(2)
            yield Static("02 / AUDIO INPUT", classes="eyebrow")
            yield Static("Can ODIA hear you clearly?", classes="wizard-title")
            yield Static(
                f"Playback output: [b]{self.audio_output.info.name}[/b]",
                classes="device-badge",
            )
            yield Static(
                "Monitor while saying “Hello”, stop the recording, then play it back.",
                classes="wizard-copy",
            )
            yield Label("Audio input", classes="field-label")
            yield Select[int](
                [],
                prompt="Choose a microphone",
                allow_blank=True,
                id="audio-input",
            )
            level = ProgressBar(
                total=60,
                show_percentage=False,
                show_eta=False,
                id="input-level",
            )
            level.display = False
            yield level
            with Horizontal(classes="action-row three-actions"):
                yield Button("Monitor", id="monitor-input", disabled=True)
                yield Button("▶  Playback", id="play-recording", disabled=True)
                yield Button(
                    "Next  →",
                    id="next-input",
                    variant="primary",
                    disabled=True,
                )
            yield Checkbox(
                "Yes, my recorded voice sounds clear",
                id="confirm-input",
                disabled=True,
                classes="confirmation",
            )
            yield Static("Finding audio inputs…", id="input-status", classes="status")
        yield Footer()

    def on_mount(self) -> None:
        try:
            inputs = AudioInput.list_devices()
        except (RuntimeError, sd.PortAudioError) as error:
            inputs = []
            self.query_one("#input-status", Static).update(
                f"Audio input discovery failed: {error}"
            )

        self.inputs = {audio_input.index: audio_input for audio_input in inputs}
        self.query_one("#audio-input", Select).set_options(
            (audio_input.name, audio_input.index) for audio_input in inputs
        )
        self.query_one("#input-status", Static).update(
            "Select an input to begin." if inputs else "No audio inputs were found."
        )

    @on(Select.Changed, "#audio-input")
    def input_changed(self) -> None:
        self._recording = None
        self._playback_succeeded = False
        confirmation = self.query_one("#confirm-input", Checkbox)
        confirmation.value = False
        confirmation.disabled = True
        selection = self.query_one("#audio-input", Select).selection
        self.query_one("#monitor-input", Button).disabled = selection is None
        self.query_one("#play-recording", Button).disabled = True
        self.query_one("#next-input", Button).disabled = True
        if selection is not None:
            self.query_one("#input-status", Static).update(
                "Ready. Choose Monitor and say “Hello”."
            )

    @on(Button.Pressed, "#monitor-input")
    def toggle_monitor(self) -> None:
        if self._monitoring:
            self._monitoring = False
            self.query_one("#monitor-input", Button).disabled = True
            self.query_one("#input-status", Static).update("Finishing recording…")
            if self._stop_event is not None:
                self._stop_event.set()
            return

        input_index = self.query_one("#audio-input", Select).selection
        if input_index is None:
            return

        self._recording = None
        self._playback_succeeded = False
        self._busy = True
        self._monitoring = True
        self._stop_event = Event()
        confirmation = self.query_one("#confirm-input", Checkbox)
        confirmation.value = False
        confirmation.disabled = True
        self.query_one("#audio-input", Select).disabled = True
        self.query_one("#monitor-input", Button).label = "Done"
        self.query_one("#play-recording", Button).disabled = True
        self.query_one("#next-input", Button).disabled = True
        level = self.query_one("#input-level", ProgressBar)
        level.update(progress=0)
        level.display = True
        self.query_one("#input-status", Static).update(
            "Say “Hello” — watch the level — then choose Done."
        )
        self.run_input_monitor(
            AudioInput(self.inputs[input_index]),
            self._stop_event,
        )

    @work(thread=True, exclusive=True, group="input-monitor")
    def run_input_monitor(self, audio_input: AudioInput, stop_event: Event) -> None:
        def report_level(decibels: float) -> None:
            self.post_message(self.LevelChanged(decibels))

        result = monitor_and_record(audio_input, stop_event, report_level)
        self.post_message(self.RecordingFinished(result))

    @on(LevelChanged)
    def level_changed(self, message: LevelChanged) -> None:
        if not self._monitoring:
            return
        progress = min(max(message.decibels + 60, 0.0), 60.0)
        self.query_one("#input-level", ProgressBar).update(progress=progress)
        self.query_one("#input-status", Static).update(
            f"Say “Hello” · {message.decibels:5.1f} dB · choose Done"
        )

    @on(RecordingFinished)
    def recording_finished(self, message: RecordingFinished) -> None:
        self._busy = False
        self._monitoring = False
        self._stop_event = None
        self.query_one("#audio-input", Select).disabled = False
        self.query_one("#monitor-input", Button).label = "Record Again"
        self.query_one("#monitor-input", Button).disabled = False
        self.query_one("#input-level", ProgressBar).display = False

        if message.result.successful and message.result.recording is not None:
            self._recording = message.result.recording
            self.query_one("#play-recording", Button).disabled = False
            recording = message.result.recording
            self.query_one("#input-status", Static).update(
                f"Recorded {recording.duration_seconds:.1f}s · "
                f"peak {recording.peak_db:.1f} dB. Choose Playback."
            )
        else:
            self.query_one("#input-status", Static).update(
                f"Recording failed: {message.result.error}"
            )

    @on(Button.Pressed, "#play-recording")
    def play_input_recording(self) -> None:
        if self._recording is None:
            return
        self._busy = True
        self.query_one("#audio-input", Select).disabled = True
        self.query_one("#monitor-input", Button).disabled = True
        self.query_one("#play-recording", Button).disabled = True
        self.query_one("#input-status", Static).update("Playing your recording…")
        self.run_recording_playback(self._recording)

    @work(thread=True, exclusive=True, group="recording-playback")
    def run_recording_playback(self, recording: AudioRecording) -> None:
        result = play_recording(recording, self.audio_output)
        self.post_message(self.PlaybackFinished(result))

    @on(PlaybackFinished)
    def playback_finished(self, message: PlaybackFinished) -> None:
        self._busy = False
        self.query_one("#audio-input", Select).disabled = False
        self.query_one("#monitor-input", Button).disabled = False
        self.query_one("#play-recording", Button).disabled = False
        if message.result.successful:
            self._playback_succeeded = True
            self.query_one("#confirm-input", Checkbox).disabled = False
            self.query_one("#input-status", Static).update(
                "Playback finished. Does your voice sound clear?"
            )
        else:
            self.query_one("#input-status", Static).update(
                f"Playback failed: {message.result.error}"
            )

    @on(Checkbox.Changed, "#confirm-input")
    def input_confirmation_changed(self) -> None:
        confirmed = self.query_one("#confirm-input", Checkbox).value
        self.query_one("#next-input", Button).disabled = not (
            self._playback_succeeded and confirmed
        )

    @on(Button.Pressed, "#next-input")
    def finish_input(self) -> None:
        input_index = self.query_one("#audio-input", Select).selection
        if input_index is not None:
            self.dismiss(AudioInput(self.inputs[input_index]))

    def on_unmount(self) -> None:
        if self._stop_event is not None:
            self._stop_event.set()


class CameraScreen(Screen[Camera]):
    """Run separate still-camera and live-stream tests."""

    class CameraTestFinished(Message):
        def __init__(
            self,
            mode: CameraPreviewMode,
            result: CameraPreviewResult,
        ) -> None:
            self.mode = mode
            self.result = result
            super().__init__()

    def __init__(self) -> None:
        super().__init__()
        self.cameras: dict[int, CameraInfo] = {}
        self._busy = False
        self._camera_test_succeeded = False
        self._streaming_test_succeeded = False

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(classes="wizard-card"):
            yield _step_rail(3)
            yield Static("03 / VIDEO INPUT", classes="eyebrow")
            yield Static("Can ODIA see the right view?", classes="wizard-title")
            yield Static(
                "First verify a still image, then test the live video stream.",
                classes="wizard-copy",
            )
            yield Label("Video input", classes="field-label")
            yield Select[int](
                [],
                prompt="Choose a camera",
                allow_blank=True,
                id="camera-input",
            )
            yield Static(
                "[dim]Close each camera window with Q or Escape when you have "
                "finished reviewing it.[/]",
                classes="camera-instructions",
            )
            with Horizontal(classes="action-row three-actions"):
                yield Button("Start Camera Test", id="test-camera", disabled=True)
                yield Button(
                    "Start Streaming Test",
                    id="test-camera-stream",
                    disabled=True,
                )
                yield Button(
                    "Next  →",
                    id="next-camera",
                    variant="primary",
                    disabled=True,
                )
            yield Checkbox(
                "Yes, the camera image and live stream look correct",
                id="confirm-camera",
                disabled=True,
                classes="confirmation",
            )
            yield Static("Finding cameras…", id="camera-status", classes="status")
        yield Footer()

    def on_mount(self) -> None:
        try:
            cameras = Camera.list_devices()
        except RuntimeError as error:
            cameras = []
            self.query_one("#camera-status", Static).update(
                f"Camera discovery failed: {error}"
            )

        self.cameras = {camera.index: camera for camera in cameras}
        self.query_one("#camera-input", Select).set_options(
            (camera.name, camera.index) for camera in cameras
        )
        self.query_one("#camera-status", Static).update(
            "Select a camera to begin." if cameras else "No cameras were found."
        )

    @on(Select.Changed, "#camera-input")
    def camera_changed(self) -> None:
        self._camera_test_succeeded = False
        self._streaming_test_succeeded = False
        confirmation = self.query_one("#confirm-camera", Checkbox)
        confirmation.value = False
        confirmation.disabled = True
        selection = self.query_one("#camera-input", Select).selection
        self.query_one("#test-camera", Button).disabled = (
            selection is None or self._busy
        )
        self.query_one("#test-camera-stream", Button).disabled = True
        self.query_one("#next-camera", Button).disabled = True
        if selection is not None:
            self.query_one("#camera-status", Static).update(
                "Ready. Start with the camera test."
            )

    @on(Button.Pressed, "#test-camera")
    def start_camera_test(self) -> None:
        camera_index = self.query_one("#camera-input", Select).selection
        if camera_index is None:
            return
        self._camera_test_succeeded = False
        self._streaming_test_succeeded = False
        confirmation = self.query_one("#confirm-camera", Checkbox)
        confirmation.value = False
        confirmation.disabled = True
        self.query_one("#next-camera", Button).disabled = True
        self.query_one("#camera-status", Static).update(
            "Opening a still camera preview…"
        )
        self._start_camera_preview(CameraPreviewMode.SNAPSHOT)

    @on(Button.Pressed, "#test-camera-stream")
    def start_streaming_test(self) -> None:
        if not self._camera_test_succeeded:
            return
        self._streaming_test_succeeded = False
        confirmation = self.query_one("#confirm-camera", Checkbox)
        confirmation.value = False
        confirmation.disabled = True
        self.query_one("#next-camera", Button).disabled = True
        self.query_one("#camera-status", Static).update(
            "Opening the live camera stream…"
        )
        self._start_camera_preview(CameraPreviewMode.STREAM)

    def _start_camera_preview(self, mode: CameraPreviewMode) -> None:
        camera_index = self.query_one("#camera-input", Select).selection
        if camera_index is None:
            return
        self._busy = True
        self.query_one("#camera-input", Select).disabled = True
        self.query_one("#test-camera", Button).disabled = True
        self.query_one("#test-camera-stream", Button).disabled = True
        self.run_camera_test(Camera(self.cameras[camera_index]), mode)

    @work(thread=True, exclusive=True, group="camera-test")
    def run_camera_test(self, camera: Camera, mode: CameraPreviewMode) -> None:
        result = launch_camera_preview(camera, mode)
        self.post_message(self.CameraTestFinished(mode, result))

    @on(CameraTestFinished)
    def camera_test_finished(self, message: CameraTestFinished) -> None:
        self._busy = False
        self.query_one("#camera-input", Select).disabled = False
        self.query_one("#test-camera", Button).disabled = False
        self.query_one("#test-camera-stream", Button).disabled = not (
            self._camera_test_succeeded
        )
        if message.result.successful:
            if message.mode is CameraPreviewMode.SNAPSHOT:
                self._camera_test_succeeded = True
                self.query_one("#test-camera-stream", Button).disabled = False
                self.query_one("#camera-status", Static).update(
                    "Camera test passed. Next, start the streaming test."
                )
            else:
                self._streaming_test_succeeded = True
                self.query_one("#confirm-camera", Checkbox).disabled = False
                self.query_one("#camera-status", Static).update(
                    "Streaming test completed. Does the video look correct?"
                )
        else:
            label = (
                "Camera" if message.mode is CameraPreviewMode.SNAPSHOT else "Streaming"
            )
            self.query_one("#camera-status", Static).update(
                f"{label} test failed: {message.result.error}"
            )

    @on(Checkbox.Changed, "#confirm-camera")
    def camera_confirmation_changed(self) -> None:
        confirmed = self.query_one("#confirm-camera", Checkbox).value
        self.query_one("#next-camera", Button).disabled = not (
            self._camera_test_succeeded and self._streaming_test_succeeded and confirmed
        )

    @on(Button.Pressed, "#next-camera")
    def finish_camera(self) -> None:
        camera_index = self.query_one("#camera-input", Select).selection
        if camera_index is not None:
            self.dismiss(Camera(self.cameras[camera_index]))


class SummaryScreen(Screen[Context]):
    """Present the confirmed selections as the final setup dashboard."""

    def __init__(self, session: SetupSession) -> None:
        super().__init__()
        self.session = session

    def compose(self) -> ComposeResult:
        if (
            self.session.audio_output is None
            or self.session.audio_input is None
            or self.session.camera is None
        ):
            raise RuntimeError("Cannot show a summary for incomplete setup.")

        output = self.session.audio_output.info
        audio_input = self.session.audio_input.info
        camera = self.session.camera.info

        yield Header()
        with VerticalScroll(classes="wizard-card summary-card"):
            yield _step_rail(4)
            yield Static("✓", classes="success-mark")
            yield Static("Devices Ready", classes="wizard-title summary-title")
            yield Static(
                "Your verified selections are ready for this session.",
                classes="wizard-copy",
            )
            with Horizontal(classes="summary-grid"):
                with Vertical(classes="summary-device"):
                    yield Static("🔊  AUDIO OUTPUT", classes="summary-label")
                    yield Static(output.name, classes="summary-name")
                    yield Static(
                        f"{output.channels} ch · {output.samplerate / 1000:g} kHz",
                        classes="summary-detail",
                    )
                    yield Static("✓ Confirmed", classes="verified")
                with Vertical(classes="summary-device"):
                    yield Static("🎙  AUDIO INPUT", classes="summary-label")
                    yield Static(audio_input.name, classes="summary-name")
                    yield Static(
                        f"{audio_input.channels} ch · "
                        f"{audio_input.samplerate / 1000:g} kHz",
                        classes="summary-detail",
                    )
                    yield Static("✓ Confirmed", classes="verified")
                with Vertical(classes="summary-device"):
                    yield Static("📷  VIDEO INPUT", classes="summary-label")
                    yield Static(camera.name, classes="summary-name")
                    yield Static("Snapshot · Live stream", classes="summary-detail")
                    yield Static("✓ Confirmed", classes="verified")
            yield Button(
                "Use These Devices  →",
                id="finish-setup",
                variant="success",
                classes="primary-action",
            )
        yield Footer()

    @on(Button.Pressed, "#finish-setup")
    def finish_setup(self) -> None:
        self.dismiss(self.session.build_context())
