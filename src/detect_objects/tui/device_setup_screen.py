"""Sequential Textual wizard for selecting and verifying runtime devices."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Event

import sounddevice as sd
from textual import on, work
from textual.app import ComposeResult
from textual.containers import Center, Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.screen import Screen
from textual.widgets import (
    Button,
    Digits,
    Footer,
    Header,
    Label,
    ProgressBar,
    Select,
    Static,
)

from ..device_setup import (
    AudioInput,
    AudioInputInfo,
    AudioOutput,
    AudioOutputInfo,
    AudioOutputProbeResult,
    AudioRecording,
    Camera,
    CameraInfo,
    Context,
    Environment,
    PlaybackResult,
    RecordingResult,
    monitor_and_record,
    play_recording,
    probe_audio_output,
)
from ..models import (
    ModelSelection,
    get_model_option,
    list_model_options,
)
from ..opencv_preview.camera_preview import (
    CameraPreviewMode,
    CameraPreviewResult,
    launch_camera_preview,
)
from ..ui_theme import DEFAULT_UI_THEME, UI_THEME_OPTIONS


@dataclass(frozen=True)
class SetupNavigation:
    """Request a direct move to an available setup tab."""

    step: int
    value: object | None = None


def _step_tabs(active: int, available: int) -> Center:
    """Build keyboard-focusable tabs for the available setup steps."""
    labels = ("SPEAKER", "MIC", "VIDEO", "MODELS", "READY")
    tabs: list[Button] = []
    for position, label in enumerate(labels, start=1):
        if position == active:
            prefix = "●"
            state_class = "step-tab-current"
        elif position < available:
            prefix = "✓"
            state_class = "step-tab-complete"
        else:
            prefix = "○"
            state_class = "step-tab-locked"
        tabs.append(
            Button(
                f"{prefix}  {label}",
                id=f"setup-tab-{position}",
                classes=f"step-tab {state_class}",
                disabled=position == active or position > available,
            )
        )
    return Center(
        Horizontal(*tabs, classes="step-tabs"),
        classes="step-tabs-frame",
    )


class SetupScreen(Screen):
    """Base screen that turns the setup rail into direct navigation tabs."""

    def __init__(self, *, active_step: int, available_step: int) -> None:
        super().__init__()
        self.active_step = active_step
        self.available_step = available_step

    def current_selection(self) -> object | None:
        """Return the current screen value so tab navigation does not lose it."""
        return None

    @on(Button.Pressed, ".step-tab")
    def navigate_to_step(self, event: Button.Pressed) -> None:
        if getattr(self, "_busy", False):
            return
        target = int((event.button.id or "").removeprefix("setup-tab-"))
        if target <= self.available_step and target != self.active_step:
            self.dismiss(SetupNavigation(target, self.current_selection()))


@dataclass
class SetupSession:
    """Selections confirmed while the user advances through the wizard."""

    audio_output: AudioOutput | None = None
    audio_input: AudioInput | None = None
    camera: Camera | None = None
    models: ModelSelection | None = None

    @property
    def available_step(self) -> int:
        """Return the furthest setup tab whose prerequisites are complete."""
        if self.audio_output is None:
            return 1
        if self.audio_input is None:
            return 2
        if self.camera is None:
            return 3
        if self.models is None:
            return 4
        return 5

    def build_context(self) -> Context:
        """Create the runtime context after every device is confirmed."""
        if (
            self.audio_output is None
            or self.audio_input is None
            or self.camera is None
            or self.models is None
        ):
            raise RuntimeError("Device setup is incomplete.")
        return Context(
            environment=Environment.detect(),
            camera=self.camera,
            audio_input=self.audio_input,
            audio_output=self.audio_output,
            models=self.models,
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
                "Four guided choices · about two minutes",
                classes="hero-note",
            )
            with Horizontal(classes="theme-picker"):
                yield Label("TUI theme", classes="theme-label")
                yield Select[str](
                    UI_THEME_OPTIONS,
                    allow_blank=False,
                    value=DEFAULT_UI_THEME,
                    id="ui-theme",
                )
            with Vertical(classes="feature-list"):
                with Horizontal(classes="feature-row"):
                    yield Digits("01", classes="feature-number")
                    yield Label("SPEAKER", classes="feature-title")
                    yield Static(
                        "Speakers · optional test",
                        classes="feature-copy",
                    )
                with Horizontal(classes="feature-row"):
                    yield Digits("02", classes="feature-number")
                    yield Label("MIC", classes="feature-title")
                    yield Static(
                        "Microphone · optional test",
                        classes="feature-copy",
                    )
                with Horizontal(classes="feature-row"):
                    yield Digits("03", classes="feature-number")
                    yield Label("VIDEO", classes="feature-title")
                    yield Static(
                        "Camera · optional test",
                        classes="feature-copy",
                    )
                with Horizontal(classes="feature-row"):
                    yield Digits("04", classes="feature-number")
                    yield Label("AI MODELS", classes="feature-title")
                    yield Static(
                        "Vision and voice models",
                        classes="feature-copy",
                    )
            yield Button(
                "Begin Setup  →",
                id="begin-setup",
                variant="primary",
                classes="primary-action",
            )
        yield Footer()

    @on(Select.Changed, "#ui-theme")
    def theme_changed(self) -> None:
        """Apply the selected theme immediately to every setup screen."""
        theme_name = self.query_one("#ui-theme", Select).selection
        if theme_name is not None:
            self.app.theme = theme_name

    @on(Button.Pressed, "#begin-setup")
    def begin_setup(self) -> None:
        self.dismiss(True)


class AudioOutputScreen(SetupScreen):
    """Select an output and optionally play a cat sample."""

    class SampleFinished(Message):
        def __init__(self, result: AudioOutputProbeResult) -> None:
            self.result = result
            super().__init__()

    def __init__(
        self,
        selected_output: AudioOutput | None = None,
        *,
        available_step: int = 1,
    ) -> None:
        super().__init__(active_step=1, available_step=available_step)
        self.selected_output = selected_output
        self.outputs: dict[int, AudioOutputInfo] = {}
        self._busy = False

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(classes="wizard-card"):
            yield _step_tabs(1, self.available_step)
            yield Static("01 / SPEAKER", classes="eyebrow")
            yield Static("Where should ODIA play sound?", classes="wizard-title")
            yield Static(
                "Choose an output and continue, or optionally play the cat sample.",
                classes="wizard-copy",
            )
            yield Label("Speaker", classes="field-label")
            yield Select[int](
                [],
                prompt="Choose speakers or headphones",
                allow_blank=True,
                id="audio-output",
            )
            with Horizontal(classes="action-row three-actions"):
                yield Button("←  Previous", id="prev-output")
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
            yield Static("Finding speakers…", id="output-status", classes="status")
        yield Footer()

    def on_mount(self) -> None:
        try:
            outputs = AudioOutput.list_devices()
        except (RuntimeError, sd.PortAudioError) as error:
            outputs = []
            self.query_one("#output-status", Static).update(
                f"Speaker discovery failed: {error}"
            )

        self.outputs = {output.index: output for output in outputs}
        self.query_one("#audio-output", Select).set_options(
            (output.name, output.index) for output in outputs
        )
        if (
            self.selected_output is not None
            and self.selected_output.info.index in self.outputs
        ):
            self.query_one("#audio-output", Select).value = (
                self.selected_output.info.index
            )
        if outputs:
            self.query_one("#output-status", Static).update(
                "Select an output to enable the sample."
            )
        else:
            self.query_one("#output-status", Static).update(
                "No speakers or headphones were found."
            )

    @on(Select.Changed, "#audio-output")
    def output_changed(self) -> None:
        selection = self.query_one("#audio-output", Select).selection
        self.query_one("#play-output-sample", Button).disabled = (
            selection is None or self._busy
        )
        self.query_one("#next-output", Button).disabled = selection is None
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
        self.query_one("#prev-output", Button).disabled = True
        self.query_one("#play-output-sample", Button).disabled = True
        self.query_one("#next-output", Button).disabled = True
        self.query_one("#output-status", Static).update("Playing cat meow…")
        self.run_output_sample(AudioOutput(self.outputs[output_index]))

    @work(thread=True, exclusive=True, group="output-sample")
    def run_output_sample(self, output: AudioOutput) -> None:
        self.post_message(self.SampleFinished(probe_audio_output(output)))

    @on(SampleFinished)
    def sample_finished(self, message: SampleFinished) -> None:
        self._busy = False
        self.query_one("#audio-output", Select).disabled = False
        self.query_one("#prev-output", Button).disabled = False
        self.query_one("#play-output-sample", Button).disabled = False
        self.query_one("#next-output", Button).disabled = False
        if message.result.available:
            self.query_one("#output-status", Static).update(
                "Sample playback completed."
            )
        else:
            self.query_one("#output-status", Static).update(
                f"Speaker test failed: {message.result.error}"
            )

    @on(Button.Pressed, "#prev-output")
    def previous_output(self) -> None:
        if not self._busy:
            self.dismiss(None)

    @on(Button.Pressed, "#next-output")
    def finish_output(self) -> None:
        selection = self.current_selection()
        if selection is not None:
            self.dismiss(selection)

    def current_selection(self) -> AudioOutput | None:
        output_index = self.query_one("#audio-output", Select).selection
        return (
            AudioOutput(self.outputs[output_index])
            if output_index is not None
            else None
        )


class AudioInputScreen(SetupScreen):
    """Select an input and optionally record and play it back."""

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

    def __init__(
        self,
        audio_output: AudioOutput,
        selected_input: AudioInput | None = None,
        *,
        available_step: int = 2,
    ) -> None:
        super().__init__(active_step=2, available_step=available_step)
        self.audio_output = audio_output
        self.selected_input = selected_input
        self.inputs: dict[int, AudioInputInfo] = {}
        self._monitoring = False
        self._busy = False
        self._stop_event: Event | None = None
        self._recording: AudioRecording | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(classes="wizard-card"):
            yield _step_tabs(2, self.available_step)
            yield Static("02 / MIC", classes="eyebrow")
            yield Static("Can ODIA hear you clearly?", classes="wizard-title")
            yield Static(
                f"Playback speaker: [b]{self.audio_output.info.name}[/b]",
                classes="device-badge",
            )
            yield Static(
                "Choose an input and continue, or optionally record and play it back.",
                classes="wizard-copy",
            )
            yield Label("Microphone", classes="field-label")
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
            with Horizontal(classes="action-row four-actions"):
                yield Button("←  Previous", id="prev-input")
                yield Button("Monitor", id="monitor-input", disabled=True)
                yield Button("▶  Playback", id="play-recording", disabled=True)
                yield Button(
                    "Next  →",
                    id="next-input",
                    variant="primary",
                    disabled=True,
                )
            yield Static("Finding microphones…", id="input-status", classes="status")
        yield Footer()

    def on_mount(self) -> None:
        try:
            inputs = AudioInput.list_devices()
        except (RuntimeError, sd.PortAudioError) as error:
            inputs = []
            self.query_one("#input-status", Static).update(
                f"Microphone discovery failed: {error}"
            )

        self.inputs = {audio_input.index: audio_input for audio_input in inputs}
        self.query_one("#audio-input", Select).set_options(
            (audio_input.name, audio_input.index) for audio_input in inputs
        )
        if (
            self.selected_input is not None
            and self.selected_input.info.index in self.inputs
        ):
            self.query_one("#audio-input", Select).value = (
                self.selected_input.info.index
            )
        self.query_one("#input-status", Static).update(
            "Select a microphone to begin." if inputs else "No microphones were found."
        )

    @on(Select.Changed, "#audio-input")
    def input_changed(self) -> None:
        self._recording = None
        selection = self.query_one("#audio-input", Select).selection
        self.query_one("#monitor-input", Button).disabled = selection is None
        self.query_one("#play-recording", Button).disabled = True
        self.query_one("#next-input", Button).disabled = selection is None
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
        self._busy = True
        self._monitoring = True
        self._stop_event = Event()
        self.query_one("#audio-input", Select).disabled = True
        self.query_one("#prev-input", Button).disabled = True
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
        self.query_one("#prev-input", Button).disabled = False
        self.query_one("#monitor-input", Button).label = "Record Again"
        self.query_one("#monitor-input", Button).disabled = False
        self.query_one("#input-level", ProgressBar).display = False
        self.query_one("#next-input", Button).disabled = False

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
        self.query_one("#prev-input", Button).disabled = True
        self.query_one("#monitor-input", Button).disabled = True
        self.query_one("#play-recording", Button).disabled = True
        self.query_one("#next-input", Button).disabled = True
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
        self.query_one("#prev-input", Button).disabled = False
        self.query_one("#monitor-input", Button).disabled = False
        self.query_one("#play-recording", Button).disabled = False
        self.query_one("#next-input", Button).disabled = False
        if message.result.successful:
            self.query_one("#input-status", Static).update(
                "Recording playback completed."
            )
        else:
            self.query_one("#input-status", Static).update(
                f"Playback failed: {message.result.error}"
            )

    @on(Button.Pressed, "#prev-input")
    def previous_input(self) -> None:
        if not self._busy and not self._monitoring:
            self.dismiss(None)

    @on(Button.Pressed, "#next-input")
    def finish_input(self) -> None:
        selection = self.current_selection()
        if selection is not None:
            self.dismiss(selection)

    def current_selection(self) -> AudioInput | None:
        input_index = self.query_one("#audio-input", Select).selection
        return AudioInput(self.inputs[input_index]) if input_index is not None else None

    def on_unmount(self) -> None:
        if self._stop_event is not None:
            self._stop_event.set()


class CameraScreen(SetupScreen):
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

    def __init__(
        self,
        selected_camera: Camera | None = None,
        *,
        available_step: int = 3,
    ) -> None:
        super().__init__(active_step=3, available_step=available_step)
        self.selected_camera = selected_camera
        self.cameras: dict[int, CameraInfo] = {}
        self._busy = False
        self._camera_test_succeeded = False

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(classes="wizard-card"):
            yield _step_tabs(3, self.available_step)
            yield Static("03 / VIDEO", classes="eyebrow")
            yield Static("Can ODIA see the right view?", classes="wizard-title")
            yield Static(
                "Choose a camera and continue, or optionally test its image and stream.",
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
            with Horizontal(classes="action-row four-actions"):
                yield Button("←  Previous", id="prev-camera")
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
        if (
            self.selected_camera is not None
            and self.selected_camera.info.index in self.cameras
        ):
            self.query_one("#camera-input", Select).value = (
                self.selected_camera.info.index
            )
        self.query_one("#camera-status", Static).update(
            "Select a camera to begin." if cameras else "No cameras were found."
        )

    @on(Select.Changed, "#camera-input")
    def camera_changed(self) -> None:
        self._camera_test_succeeded = False
        selection = self.query_one("#camera-input", Select).selection
        self.query_one("#test-camera", Button).disabled = (
            selection is None or self._busy
        )
        self.query_one("#test-camera-stream", Button).disabled = True
        self.query_one("#next-camera", Button).disabled = selection is None
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
        self.query_one("#next-camera", Button).disabled = True
        self.query_one("#camera-status", Static).update(
            "Opening a still camera preview…"
        )
        self._start_camera_preview(CameraPreviewMode.SNAPSHOT)

    @on(Button.Pressed, "#test-camera-stream")
    def start_streaming_test(self) -> None:
        if not self._camera_test_succeeded:
            return
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
        self.query_one("#prev-camera", Button).disabled = True
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
        self.query_one("#prev-camera", Button).disabled = False
        self.query_one("#test-camera", Button).disabled = False
        self.query_one("#test-camera-stream", Button).disabled = not (
            self._camera_test_succeeded
        )
        self.query_one("#next-camera", Button).disabled = False
        if message.result.successful:
            if message.mode is CameraPreviewMode.SNAPSHOT:
                self._camera_test_succeeded = True
                self.query_one("#test-camera-stream", Button).disabled = False
                self.query_one("#camera-status", Static).update(
                    "Camera test passed. Next, start the streaming test."
                )
            else:
                self.query_one("#camera-status", Static).update(
                    "Streaming test completed."
                )
        else:
            label = (
                "Camera" if message.mode is CameraPreviewMode.SNAPSHOT else "Streaming"
            )
            self.query_one("#camera-status", Static).update(
                f"{label} test failed: {message.result.error}"
            )

    @on(Button.Pressed, "#prev-camera")
    def previous_camera(self) -> None:
        if not self._busy:
            self.dismiss(None)

    @on(Button.Pressed, "#next-camera")
    def finish_camera(self) -> None:
        selection = self.current_selection()
        if selection is not None:
            self.dismiss(selection)

    def current_selection(self) -> Camera | None:
        camera_index = self.query_one("#camera-input", Select).selection
        return Camera(self.cameras[camera_index]) if camera_index is not None else None


class ModelSelectionScreen(SetupScreen):
    """Choose the vision and voice model presets for this run."""

    def __init__(
        self,
        selected_models: ModelSelection | None = None,
        *,
        available_step: int = 4,
    ) -> None:
        super().__init__(active_step=4, available_step=available_step)
        self.selected_models = selected_models or ModelSelection()

    def compose(self) -> ComposeResult:
        vision_options = list_model_options("vision")
        voice_options = list_model_options("voice")

        yield Header()
        with VerticalScroll(classes="wizard-card"):
            yield _step_tabs(4, self.available_step)
            yield Static("04 / AI MODELS", classes="eyebrow")
            yield Static("How should ODIA see and listen?", classes="wizard-title")
            yield Static(
                "Choose model presets for this session. Recommended defaults are "
                "selected automatically.",
                classes="wizard-copy",
            )

            yield Label("Vision model", classes="field-label")
            yield Select[str](
                [(option.display_name, option.id) for option in vision_options],
                allow_blank=False,
                value=self.selected_models.vision_id,
                id="vision-model",
            )
            yield Static(
                get_model_option(self.selected_models.vision_id).description,
                id="vision-model-description",
                classes="model-description",
            )

            yield Label("Voice model", classes="field-label")
            yield Select[str](
                [(option.display_name, option.id) for option in voice_options],
                allow_blank=False,
                value=self.selected_models.voice_id,
                id="voice-model",
            )
            yield Static(
                get_model_option(self.selected_models.voice_id).description,
                id="voice-model-description",
                classes="model-description",
            )

            with Horizontal(classes="action-row navigation-row"):
                yield Button("←  Previous", id="prev-models")
                yield Button(
                    "Review Setup  →",
                    id="next-models",
                    variant="primary",
                )
        yield Footer()

    @on(Select.Changed, "#vision-model")
    def vision_model_changed(self) -> None:
        model_id = self.query_one("#vision-model", Select).selection
        if model_id is not None:
            option = get_model_option(model_id, kind="vision")
            self.query_one("#vision-model-description", Static).update(
                option.description
            )
        self._update_next_button()

    @on(Select.Changed, "#voice-model")
    def voice_model_changed(self) -> None:
        model_id = self.query_one("#voice-model", Select).selection
        if model_id is not None:
            option = get_model_option(model_id, kind="voice")
            self.query_one("#voice-model-description", Static).update(
                option.description
            )
        self._update_next_button()

    def _update_next_button(self) -> None:
        vision_id = self.query_one("#vision-model", Select).selection
        voice_id = self.query_one("#voice-model", Select).selection
        self.query_one("#next-models", Button).disabled = (
            vision_id is None or voice_id is None
        )

    @on(Button.Pressed, "#prev-models")
    def previous_models(self) -> None:
        self.dismiss(None)

    @on(Button.Pressed, "#next-models")
    def finish_models(self) -> None:
        selection = self.current_selection()
        if selection is not None:
            self.dismiss(selection)

    def current_selection(self) -> ModelSelection | None:
        vision_id = self.query_one("#vision-model", Select).selection
        voice_id = self.query_one("#voice-model", Select).selection
        if vision_id is None or voice_id is None:
            return None
        return ModelSelection(
            vision_id=vision_id,
            voice_id=voice_id,
        )


class SummaryScreen(SetupScreen):
    """Present the confirmed selections as the final setup dashboard."""

    def __init__(self, session: SetupSession) -> None:
        super().__init__(active_step=5, available_step=5)
        self.session = session

    def compose(self) -> ComposeResult:
        if (
            self.session.audio_output is None
            or self.session.audio_input is None
            or self.session.camera is None
            or self.session.models is None
        ):
            raise RuntimeError("Cannot show a summary for incomplete setup.")

        output = self.session.audio_output.info
        audio_input = self.session.audio_input.info
        camera = self.session.camera.info
        vision_model = get_model_option(
            self.session.models.vision_id,
            kind="vision",
        )
        voice_model = get_model_option(
            self.session.models.voice_id,
            kind="voice",
        )

        yield Header()
        with VerticalScroll(classes="wizard-card summary-card"):
            yield _step_tabs(5, self.available_step)
            yield Static("✓", classes="success-mark")
            yield Static("ODIA Ready", classes="wizard-title summary-title")
            yield Static(
                "Your verified devices and model presets are ready for this session.",
                classes="wizard-copy",
            )
            with Vertical(classes="summary-table"):
                with Horizontal(classes="summary-table-header"):
                    yield Static("SETUP", classes="summary-table-label")
                    yield Static("SELECTION", classes="summary-table-value")
                    yield Static("DETAIL", classes="summary-table-detail")
                with Horizontal(classes="summary-table-row"):
                    yield Static("✓  SPEAKER", classes="summary-table-label")
                    yield Static(output.name, classes="summary-table-value")
                    yield Static(
                        f"{output.channels} ch · {output.samplerate / 1000:g} kHz",
                        classes="summary-table-detail",
                    )
                with Horizontal(classes="summary-table-row"):
                    yield Static("✓  MIC", classes="summary-table-label")
                    yield Static(audio_input.name, classes="summary-table-value")
                    yield Static(
                        f"{audio_input.channels} ch · "
                        f"{audio_input.samplerate / 1000:g} kHz",
                        classes="summary-table-detail",
                    )
                with Horizontal(classes="summary-table-row"):
                    yield Static("✓  VIDEO", classes="summary-table-label")
                    yield Static(camera.name, classes="summary-table-value")
                    yield Static(
                        "Snapshot · Stream",
                        classes="summary-table-detail",
                    )
                with Horizontal(classes="summary-table-row"):
                    yield Static("✓  VISION MODEL", classes="summary-table-label")
                    yield Static(vision_model.name, classes="summary-table-value")
                    yield Static(
                        "Recommended" if vision_model.recommended else "Selected",
                        classes="summary-table-detail",
                    )
                with Horizontal(classes="summary-table-row"):
                    yield Static("✓  VOICE MODEL", classes="summary-table-label")
                    yield Static(voice_model.name, classes="summary-table-value")
                    yield Static(
                        "Recommended" if voice_model.recommended else "Selected",
                        classes="summary-table-detail",
                    )
            with Horizontal(classes="action-row navigation-row"):
                yield Button("←  Previous", id="prev-summary")
                yield Button(
                    "Choose Runtime  →",
                    id="finish-setup",
                    variant="success",
                )
        yield Footer()

    @on(Button.Pressed, "#prev-summary")
    def previous_summary(self) -> None:
        self.dismiss(None)

    @on(Button.Pressed, "#finish-setup")
    def finish_setup(self) -> None:
        self.dismiss(self.session.build_context())
