"""Headless tests for the sequential Textual device-setup wizard."""

from __future__ import annotations

import unittest
from unittest.mock import patch

import cv2
import numpy as np
from cv2_enumerate_cameras.camera_info import CameraInfo
from textual.widgets import Button, Digits, Label, ProgressBar, Select, Static

from detect_objects.device_setup import (
    AudioInput,
    AudioInputInfo,
    AudioOutput,
    AudioOutputInfo,
    AudioOutputProbeResult,
    AudioRecording,
    Camera,
    Context,
    PlaybackResult,
    RecordingResult,
)
from detect_objects.launch_mode import RuntimeMode
from detect_objects.opencv_preview.camera_preview import (
    CameraPreviewMode,
    CameraPreviewResult,
)
from detect_objects.models import (
    DEFAULT_VISION_MODEL_ID,
    ModelSelection,
)
from detect_objects.runtime import STARTUP_STEPS, StartupUpdate
from detect_objects.tui.app import OdiaApp, StartupApp
from detect_objects.tui.device_setup_screen import (
    AudioInputScreen,
    AudioOutputScreen,
    CameraScreen,
    ModelSelectionScreen,
    SummaryScreen,
    WelcomeScreen,
)
from detect_objects.tui.startup_screen import StartupScreen
from detect_objects.tui.runtime_mode_screen import RuntimeModeScreen
from detect_objects.ui_theme import DEFAULT_UI_THEME, UI_THEME_NAMES


class OdiaAppTests(unittest.IsolatedAsyncioTestCase):
    """Verify the gated wizard flow using fake devices and hardware results."""

    def setUp(self) -> None:
        self.camera = CameraInfo(
            2,
            "Test Camera",
            "/dev/test-camera",
            None,
            None,
            cv2.CAP_ANY,
        )
        self.audio_input = AudioInputInfo(
            index=7,
            name="Test Microphone",
            channels=1,
            samplerate=16000.0,
        )
        self.audio_output = AudioOutputInfo(
            index=8,
            name="Test Speakers",
            channels=2,
            samplerate=48000.0,
        )

    async def test_starts_on_polished_welcome_page(self) -> None:
        app = OdiaApp()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()

            self.assertEqual(app.theme, DEFAULT_UI_THEME)
            self.assertFalse(app.current_theme.ansi)
            self.assertEqual(app.current_theme.background, "#100F0F")
            self.assertIsInstance(app.screen, WelcomeScreen)
            theme_select = app.screen.query_one("#ui-theme", Select)
            self.assertEqual(theme_select.selection, DEFAULT_UI_THEME)
            for theme_name in UI_THEME_NAMES:
                theme_select.value = theme_name
                await pilot.pause()
                self.assertEqual(app.theme, theme_name)
            content = " ".join(
                str(widget.content) for widget in app.screen.query(Static)
            )
            self.assertIn("DEVICE SETUP", content)
            self.assertIn("hear, speak, and be seen", content)
            numbers = [str(widget.value) for widget in app.screen.query(Digits)]
            self.assertEqual(numbers, ["01", "02", "03", "04"])
            labels = " ".join(str(widget.content) for widget in app.screen.query(Label))
            self.assertIn("SPEAKER", labels)
            self.assertIn("MIC", labels)
            self.assertIn("VIDEO", labels)
            self.assertIn("AI MODELS", labels)
            self.assertIsNotNone(app.screen.query_one("#begin-setup", Button))

    async def test_completed_setup_steps_can_be_opened_from_tabs(self) -> None:
        with (
            patch.object(AudioOutput, "list_devices", return_value=[self.audio_output]),
            patch.object(AudioInput, "list_devices", return_value=[self.audio_input]),
            patch.object(Camera, "list_devices", return_value=[self.camera]),
        ):
            app = OdiaApp()
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.click("#begin-setup")
                await pilot.pause()

                self.assertTrue(app.screen.query_one("#setup-tab-1", Button).disabled)
                self.assertTrue(app.screen.query_one("#setup-tab-2", Button).disabled)
                expected_tab_width = app.screen.query_one(
                    "#setup-tab-1", Button
                ).region.width
                app.screen.query_one("#audio-output", Select).value = (
                    self.audio_output.index
                )
                await pilot.pause()
                await pilot.click("#next-output")
                await pilot.pause()

                self.assertIsInstance(app.screen, AudioInputScreen)
                self.assertFalse(app.screen.query_one("#setup-tab-1", Button).disabled)
                self.assertTrue(app.screen.query_one("#setup-tab-2", Button).disabled)
                app.screen.query_one("#audio-input", Select).value = (
                    self.audio_input.index
                )
                await pilot.pause()
                await pilot.click("#next-input")
                await pilot.pause()

                self.assertIsInstance(app.screen, CameraScreen)
                self.assertTrue(app.screen.query_one("#setup-tab-3", Button).disabled)
                await pilot.click("#setup-tab-1")
                await pilot.pause()

                self.assertIsInstance(app.screen, AudioOutputScreen)
                self.assertEqual(
                    app.screen.query_one("#audio-output", Select).selection,
                    self.audio_output.index,
                )
                self.assertFalse(app.screen.query_one("#setup-tab-3", Button).disabled)
                await pilot.click("#setup-tab-3")
                await pilot.pause()

                self.assertIsInstance(app.screen, CameraScreen)
                app.screen.query_one("#camera-input", Select).value = self.camera.index
                await pilot.pause()
                await pilot.click("#next-camera")
                await pilot.pause()
                await pilot.click("#next-models")
                await pilot.pause()

                ready_tab_widths = [
                    tab.region.width for tab in app.screen.query(".step-tab")
                ]
                self.assertEqual(ready_tab_widths, [expected_tab_width] * 5)

    async def test_completes_output_input_camera_and_summary_flow(self) -> None:
        recording = AudioRecording(
            samples=np.zeros((16000, 1), dtype=np.float32),
            samplerate=16000.0,
            duration_seconds=1.0,
            peak_db=-6.0,
        )

        def monitor(audio_input, stop_event, on_level):
            on_level(-12.0)
            stop_event.wait(timeout=2.0)
            return RecordingResult(successful=True, recording=recording)

        with (
            patch.object(AudioOutput, "list_devices", return_value=[self.audio_output]),
            patch.object(AudioInput, "list_devices", return_value=[self.audio_input]),
            patch.object(Camera, "list_devices", return_value=[self.camera]),
            patch(
                "detect_objects.tui.device_setup_screen.probe_audio_output",
                return_value=AudioOutputProbeResult(available=True),
            ) as output_probe,
            patch(
                "detect_objects.tui.device_setup_screen.monitor_and_record",
                side_effect=monitor,
            ) as input_monitor,
            patch(
                "detect_objects.tui.device_setup_screen.play_recording",
                return_value=PlaybackResult(successful=True),
            ) as recording_playback,
            patch(
                "detect_objects.tui.device_setup_screen.launch_camera_preview",
                return_value=CameraPreviewResult(successful=True),
            ) as camera_test,
        ):
            app = OdiaApp()
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                await pilot.click("#begin-setup")
                await pilot.pause()

                self.assertIsInstance(app.screen, AudioOutputScreen)
                self.assertIsNotNone(app.screen.query_one("#prev-output", Button))
                self.assertEqual(list(app.screen.query("Checkbox")), [])
                output_next = app.screen.query_one("#next-output", Button)
                self.assertTrue(output_next.disabled)
                app.screen.query_one("#audio-output", Select).value = (
                    self.audio_output.index
                )
                await pilot.pause()
                await pilot.click("#play-output-sample")
                await app.workers.wait_for_complete()
                await pilot.pause()
                self.assertFalse(output_next.disabled)
                await pilot.click("#next-output")
                await pilot.pause()

                self.assertIsInstance(app.screen, AudioInputScreen)
                self.assertIsNotNone(app.screen.query_one("#prev-input", Button))
                self.assertEqual(list(app.screen.query("Checkbox")), [])
                input_next = app.screen.query_one("#next-input", Button)
                app.screen.query_one("#audio-input", Select).value = (
                    self.audio_input.index
                )
                await pilot.pause()
                await pilot.click("#monitor-input")
                await pilot.pause(0.1)
                level = app.screen.query_one("#input-level", ProgressBar)
                self.assertTrue(level.display)
                self.assertEqual(level.progress, 48.0)
                self.assertEqual(
                    str(app.screen.query_one("#monitor-input", Button).label),
                    "Done",
                )
                await pilot.click("#monitor-input")
                await app.workers.wait_for_complete()
                await pilot.pause()
                self.assertFalse(level.display)
                self.assertFalse(
                    app.screen.query_one("#play-recording", Button).disabled
                )
                await pilot.click("#play-recording")
                await app.workers.wait_for_complete()
                await pilot.pause()
                self.assertFalse(input_next.disabled)
                await pilot.click("#next-input")
                await pilot.pause()

                self.assertIsInstance(app.screen, CameraScreen)
                self.assertIsNotNone(app.screen.query_one("#prev-camera", Button))
                self.assertEqual(list(app.screen.query("Checkbox")), [])
                camera_next = app.screen.query_one("#next-camera", Button)
                app.screen.query_one("#camera-input", Select).value = self.camera.index
                await pilot.pause()
                await pilot.click("#test-camera")
                await app.workers.wait_for_complete()
                await pilot.pause()
                streaming_test = app.screen.query_one("#test-camera-stream", Button)
                self.assertFalse(streaming_test.disabled)
                await pilot.click("#test-camera-stream")
                await app.workers.wait_for_complete()
                await pilot.pause()
                self.assertFalse(camera_next.disabled)
                await pilot.click("#next-camera")
                await pilot.pause()

                self.assertIsInstance(app.screen, ModelSelectionScreen)
                self.assertIsNotNone(app.screen.query_one("#prev-models", Button))
                vision_select = app.screen.query_one("#vision-model", Select)
                voice_select = app.screen.query_one("#voice-model", Select)
                self.assertEqual(vision_select.selection, DEFAULT_VISION_MODEL_ID)
                voice_select.value = "whisper_tiny_ko"
                await pilot.pause()
                await pilot.click("#next-models")
                await pilot.pause()

                self.assertIsInstance(app.screen, SummaryScreen)
                self.assertIsNotNone(app.screen.query_one("#prev-summary", Button))
                summary = " ".join(
                    str(widget.content) for widget in app.screen.query(Static)
                )
                self.assertIn(self.audio_output.name, summary)
                self.assertIn(self.audio_input.name, summary)
                self.assertIn(self.camera.name, summary)
                self.assertIn("YOLO-World v2 Small", summary)
                self.assertIn("Whisper Tiny", summary)
                app.screen.query_one("#finish-setup", Button).press()
                await pilot.pause()
                self.assertIsInstance(app.screen, RuntimeModeScreen)
                self.assertIsNotNone(app.screen.query_one("#prev-runtime", Button))
                await pilot.click("#mode-desktop")
                await pilot.click("#launch-runtime")
                await pilot.pause()

        context = app.return_value
        self.assertIsInstance(context, Context)
        self.assertIs(context.audio_output.info, self.audio_output)
        self.assertIs(context.audio_input.info, self.audio_input)
        self.assertIs(context.camera.info, self.camera)
        self.assertEqual(
            context.models,
            ModelSelection(
                vision_id=DEFAULT_VISION_MODEL_ID,
                voice_id="whisper_tiny_ko",
            ),
        )
        self.assertEqual(context.ui_theme, DEFAULT_UI_THEME)
        self.assertIs(context.runtime_mode, RuntimeMode.DESKTOP)
        output_probe.assert_called_once()
        input_monitor.assert_called_once()
        recording_playback.assert_called_once()
        self.assertEqual(camera_test.call_count, 2)
        modes = [call.args[1] for call in camera_test.call_args_list]
        self.assertEqual(
            modes,
            [CameraPreviewMode.SNAPSHOT, CameraPreviewMode.STREAM],
        )

    async def test_can_skip_optional_device_tests(self) -> None:
        with (
            patch.object(AudioOutput, "list_devices", return_value=[self.audio_output]),
            patch.object(AudioInput, "list_devices", return_value=[self.audio_input]),
            patch.object(Camera, "list_devices", return_value=[self.camera]),
            patch(
                "detect_objects.tui.device_setup_screen.probe_audio_output"
            ) as output_probe,
            patch(
                "detect_objects.tui.device_setup_screen.monitor_and_record"
            ) as input_monitor,
            patch(
                "detect_objects.tui.device_setup_screen.launch_camera_preview"
            ) as camera_test,
        ):
            app = OdiaApp()
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                await pilot.click("#begin-setup")
                await pilot.pause()

                app.screen.query_one("#audio-output", Select).value = (
                    self.audio_output.index
                )
                await pilot.pause()
                self.assertFalse(app.screen.query_one("#next-output", Button).disabled)
                await pilot.click("#next-output")
                await pilot.pause()

                app.screen.query_one("#audio-input", Select).value = (
                    self.audio_input.index
                )
                await pilot.pause()
                self.assertFalse(app.screen.query_one("#next-input", Button).disabled)
                await pilot.click("#next-input")
                await pilot.pause()

                app.screen.query_one("#camera-input", Select).value = self.camera.index
                await pilot.pause()
                self.assertFalse(app.screen.query_one("#next-camera", Button).disabled)
                await pilot.click("#next-camera")
                await pilot.pause()

                self.assertIsInstance(app.screen, ModelSelectionScreen)
                await pilot.click("#next-models")
                await pilot.pause()
                self.assertIsInstance(app.screen, SummaryScreen)
                app.screen.query_one("#finish-setup", Button).press()
                await pilot.pause()
                self.assertIsInstance(app.screen, RuntimeModeScreen)
                await pilot.click("#launch-runtime")
                await pilot.pause()

        self.assertIsInstance(app.return_value, Context)
        self.assertIs(app.return_value.runtime_mode, RuntimeMode.DESKTOP)
        output_probe.assert_not_called()
        input_monitor.assert_not_called()
        camera_test.assert_not_called()

    async def test_previous_navigation_preserves_device_selections(self) -> None:
        with (
            patch.object(AudioOutput, "list_devices", return_value=[self.audio_output]),
            patch.object(AudioInput, "list_devices", return_value=[self.audio_input]),
            patch.object(Camera, "list_devices", return_value=[self.camera]),
        ):
            app = OdiaApp()
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.click("#begin-setup")
                await pilot.pause()

                app.screen.query_one("#audio-output", Select).value = (
                    self.audio_output.index
                )
                await pilot.pause()
                await pilot.click("#next-output")
                await pilot.pause()

                app.screen.query_one("#audio-input", Select).value = (
                    self.audio_input.index
                )
                await pilot.pause()
                await pilot.click("#next-input")
                await pilot.pause()

                app.screen.query_one("#camera-input", Select).value = self.camera.index
                await pilot.pause()
                await pilot.click("#prev-camera")
                await pilot.pause()

                self.assertIsInstance(app.screen, AudioInputScreen)
                self.assertEqual(
                    app.screen.query_one("#audio-input", Select).selection,
                    self.audio_input.index,
                )
                await pilot.click("#prev-input")
                await pilot.pause()

                self.assertIsInstance(app.screen, AudioOutputScreen)
                self.assertEqual(
                    app.screen.query_one("#audio-output", Select).selection,
                    self.audio_output.index,
                )
                await pilot.click("#prev-output")
                await pilot.pause()

                self.assertIsInstance(app.screen, WelcomeScreen)

    async def test_previous_navigation_from_runtime_preserves_later_choices(
        self,
    ) -> None:
        with (
            patch.object(AudioOutput, "list_devices", return_value=[self.audio_output]),
            patch.object(AudioInput, "list_devices", return_value=[self.audio_input]),
            patch.object(Camera, "list_devices", return_value=[self.camera]),
        ):
            app = OdiaApp()
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.click("#begin-setup")
                await pilot.pause()
                app.screen.query_one("#audio-output", Select).value = (
                    self.audio_output.index
                )
                await pilot.pause()
                await pilot.click("#next-output")
                await pilot.pause()
                app.screen.query_one("#audio-input", Select).value = (
                    self.audio_input.index
                )
                await pilot.pause()
                await pilot.click("#next-input")
                await pilot.pause()
                app.screen.query_one("#camera-input", Select).value = self.camera.index
                await pilot.pause()
                await pilot.click("#next-camera")
                await pilot.pause()

                app.screen.query_one("#voice-model", Select).value = "whisper_tiny_ko"
                await pilot.pause()
                await pilot.click("#next-models")
                await pilot.pause()
                await pilot.click("#finish-setup")
                await pilot.pause()
                await pilot.click("#prev-runtime")
                await pilot.pause()

                self.assertIsInstance(app.screen, SummaryScreen)
                await pilot.click("#prev-summary")
                await pilot.pause()

                self.assertIsInstance(app.screen, ModelSelectionScreen)
                self.assertEqual(
                    app.screen.query_one("#voice-model", Select).selection,
                    "whisper_tiny_ko",
                )
                await pilot.click("#prev-models")
                await pilot.pause()

                self.assertIsInstance(app.screen, CameraScreen)
                self.assertEqual(
                    app.screen.query_one("#camera-input", Select).selection,
                    self.camera.index,
                )


class StartupAppTests(unittest.IsolatedAsyncioTestCase):
    async def test_shows_runtime_updates_before_opening_camera(self) -> None:
        def prepare(report) -> None:
            for step in STARTUP_STEPS:
                report(StartupUpdate(step, f"{step} ready", finished=True))

        app = StartupApp(prepare, "monokai")
        async with app.run_test(size=(120, 40)) as pilot:
            await app.workers.wait_for_complete()
            await pilot.pause()

            self.assertEqual(app.theme, "monokai")
            self.assertIsInstance(app.screen, StartupScreen)
            content = " ".join(
                str(widget.content) for widget in app.screen.query(Static)
            )
            for step in STARTUP_STEPS:
                self.assertIn(f"{step} ready", content)

            finish_button = app.screen.query_one("#finish-startup", Button)
            self.assertFalse(finish_button.disabled)
            self.assertEqual(str(finish_button.label), "Open Camera  →")
            await pilot.click("#finish-startup")
            await pilot.pause()

        self.assertTrue(app.return_value)

    async def test_shows_startup_error_and_does_not_continue(self) -> None:
        def fail(report) -> None:
            raise RuntimeError("model missing")

        app = StartupApp(fail)
        async with app.run_test(size=(120, 40)) as pilot:
            await app.workers.wait_for_complete()
            await pilot.pause()

            status = app.screen.query_one("#startup-status", Static)
            self.assertIn("model missing", str(status.content))
            close_button = app.screen.query_one("#finish-startup", Button)
            self.assertFalse(close_button.disabled)
            self.assertEqual(str(close_button.label), "Close")
            await pilot.click("#finish-startup")
            await pilot.pause()

        self.assertFalse(app.return_value)


if __name__ == "__main__":
    unittest.main(verbosity=2)
