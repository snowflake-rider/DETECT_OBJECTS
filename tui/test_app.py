"""Headless tests for the sequential Textual device-setup wizard."""

from __future__ import annotations

import unittest
from unittest.mock import patch

import cv2
import numpy as np
from cv2_enumerate_cameras.camera_info import CameraInfo
from textual.widgets import Button, Checkbox, ProgressBar, Select, Static

from device_setup import (
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
from opencv_preview.camera_preview import CameraPreviewMode, CameraPreviewResult
from tui.app import OdiaApp
from tui.device_setup_screen import (
    AudioInputScreen,
    AudioOutputScreen,
    CameraScreen,
    SummaryScreen,
    WelcomeScreen,
)


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

            self.assertIsInstance(app.screen, WelcomeScreen)
            content = " ".join(
                str(widget.content) for widget in app.screen.query(Static)
            )
            self.assertIn("DEVICE SETUP", content)
            self.assertIn("hear, speak, and be seen", content)
            self.assertIsNotNone(app.screen.query_one("#begin-setup", Button))

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
                "tui.device_setup_screen.probe_audio_output",
                return_value=AudioOutputProbeResult(available=True),
            ) as output_probe,
            patch(
                "tui.device_setup_screen.monitor_and_record",
                side_effect=monitor,
            ) as input_monitor,
            patch(
                "tui.device_setup_screen.play_recording",
                return_value=PlaybackResult(successful=True),
            ) as recording_playback,
            patch(
                "tui.device_setup_screen.launch_camera_preview",
                return_value=CameraPreviewResult(successful=True),
            ) as camera_test,
        ):
            app = OdiaApp()
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                await pilot.click("#begin-setup")
                await pilot.pause()

                self.assertIsInstance(app.screen, AudioOutputScreen)
                output_next = app.screen.query_one("#next-output", Button)
                self.assertTrue(output_next.disabled)
                app.screen.query_one("#audio-output", Select).value = (
                    self.audio_output.index
                )
                await pilot.pause()
                await pilot.click("#play-output-sample")
                await app.workers.wait_for_complete()
                await pilot.pause()
                output_confirmation = app.screen.query_one("#confirm-output", Checkbox)
                self.assertFalse(output_confirmation.disabled)
                output_confirmation.value = True
                await pilot.pause()
                self.assertFalse(output_next.disabled)
                await pilot.click("#next-output")
                await pilot.pause()

                self.assertIsInstance(app.screen, AudioInputScreen)
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
                input_confirmation = app.screen.query_one("#confirm-input", Checkbox)
                self.assertFalse(input_confirmation.disabled)
                input_confirmation.value = True
                await pilot.pause()
                self.assertFalse(input_next.disabled)
                await pilot.click("#next-input")
                await pilot.pause()

                self.assertIsInstance(app.screen, CameraScreen)
                camera_next = app.screen.query_one("#next-camera", Button)
                app.screen.query_one("#camera-input", Select).value = self.camera.index
                await pilot.pause()
                await pilot.click("#test-camera")
                await app.workers.wait_for_complete()
                await pilot.pause()
                camera_confirmation = app.screen.query_one("#confirm-camera", Checkbox)
                self.assertTrue(camera_confirmation.disabled)
                streaming_test = app.screen.query_one("#test-camera-stream", Button)
                self.assertFalse(streaming_test.disabled)
                await pilot.click("#test-camera-stream")
                await app.workers.wait_for_complete()
                await pilot.pause()
                self.assertFalse(camera_confirmation.disabled)
                camera_confirmation.value = True
                await pilot.pause()
                self.assertFalse(camera_next.disabled)
                await pilot.click("#next-camera")
                await pilot.pause()

                self.assertIsInstance(app.screen, SummaryScreen)
                summary = " ".join(
                    str(widget.content) for widget in app.screen.query(Static)
                )
                self.assertIn(self.audio_output.name, summary)
                self.assertIn(self.audio_input.name, summary)
                self.assertIn(self.camera.name, summary)
                await pilot.click("#finish-setup")
                await pilot.pause()

        context = app.return_value
        self.assertIsInstance(context, Context)
        self.assertIs(context.audio_output.info, self.audio_output)
        self.assertIs(context.audio_input.info, self.audio_input)
        self.assertIs(context.camera.info, self.camera)
        output_probe.assert_called_once()
        input_monitor.assert_called_once()
        recording_playback.assert_called_once()
        self.assertEqual(camera_test.call_count, 2)
        modes = [call.args[1] for call in camera_test.call_args_list]
        self.assertEqual(
            modes,
            [CameraPreviewMode.SNAPSHOT, CameraPreviewMode.STREAM],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
