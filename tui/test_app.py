"""Headless tests for the Textual application flow."""

from __future__ import annotations

import unittest
from unittest.mock import patch

import cv2
from cv2_enumerate_cameras.camera_info import CameraInfo
from textual.widgets import Button, ProgressBar, Select, Static

from device_setup import (
    AudioInput,
    AudioInputInfo,
    AudioOutput,
    AudioOutputInfo,
    Camera,
    CameraProbeResult,
    Context,
)
from audio_preview.microphone_preview import AudioPreviewResult
from opencv_preview.camera_preview import CameraPreviewMode, CameraPreviewResult
from tui.app import OdiaApp


class OdiaAppTests(unittest.IsolatedAsyncioTestCase):
    """Verify setup using fake devices instead of real hardware."""

    async def test_device_setup_returns_selected_context(self) -> None:
        camera = CameraInfo(
            2,
            "Test Camera",
            "/dev/test-camera",
            None,
            None,
            cv2.CAP_ANY,
        )
        audio_input = AudioInputInfo(
            index=7,
            name="Test Microphone",
            channels=1,
            samplerate=16000.0,
        )
        audio_output = AudioOutputInfo(
            index=8,
            name="Test Speakers",
            channels=2,
            samplerate=48000.0,
        )

        with (
            patch.object(
                Camera,
                "list_devices",
                return_value=[camera],
            ),
            patch.object(
                AudioInput,
                "list_devices",
                return_value=[audio_input],
            ),
            patch.object(
                AudioOutput,
                "list_devices",
                return_value=[audio_output],
            ),
        ):
            app = OdiaApp()
            async with app.run_test() as pilot:
                await pilot.pause()
                screen = app.screen
                continue_button = screen.query_one("#continue", Button)
                self.assertTrue(continue_button.disabled)

                screen.query_one("#camera", Select).value = camera.index
                screen.query_one("#audio-input", Select).value = audio_input.index
                screen.query_one("#audio-output", Select).value = audio_output.index
                await pilot.pause()

                self.assertFalse(continue_button.disabled)
                await pilot.click("#continue")
                await pilot.pause()

        context = app.return_value
        self.assertIsInstance(context, Context)
        self.assertIs(context.camera.info, camera)
        self.assertIs(context.audio_input.info, audio_input)
        self.assertIs(context.audio_output.info, audio_output)

    async def test_camera_button_runs_probe_and_displays_result(self) -> None:
        camera = CameraInfo(
            2,
            "Test Camera",
            "/dev/test-camera",
            None,
            None,
            cv2.CAP_ANY,
        )
        audio_input = AudioInputInfo(
            index=7,
            name="Test Microphone",
            channels=1,
            samplerate=16000.0,
        )
        audio_output = AudioOutputInfo(
            index=8,
            name="Test Speakers",
            channels=2,
            samplerate=48000.0,
        )
        probe_result = CameraProbeResult(
            available=True,
            width=1280,
            height=720,
            fps=30.0,
        )

        with (
            patch.object(Camera, "list_devices", return_value=[camera]),
            patch.object(AudioInput, "list_devices", return_value=[audio_input]),
            patch.object(AudioOutput, "list_devices", return_value=[audio_output]),
            patch(
                "tui.device_setup_screen.probe_camera",
                return_value=probe_result,
            ) as probe,
        ):
            app = OdiaApp()
            async with app.run_test() as pilot:
                await pilot.pause()
                screen = app.screen
                test_button = screen.query_one("#test-camera", Button)
                self.assertTrue(test_button.disabled)

                screen.query_one("#camera", Select).value = camera.index
                await pilot.pause()
                self.assertFalse(test_button.disabled)

                await pilot.click("#test-camera")
                await app.workers.wait_for_complete()
                await pilot.pause()

                self.assertFalse(test_button.disabled)
                status = str(screen.query_one("#status", Static).content)
                self.assertIn("Camera test passed: 1280×720, 30.0 FPS", status)

        probe.assert_called_once()

    async def test_snapshot_and_stream_buttons_launch_preview_modes(self) -> None:
        camera = CameraInfo(
            2,
            "Test Camera",
            "/dev/test-camera",
            None,
            None,
            cv2.CAP_ANY,
        )
        audio_input = AudioInputInfo(
            index=7,
            name="Test Microphone",
            channels=1,
            samplerate=16000.0,
        )
        audio_output = AudioOutputInfo(
            index=8,
            name="Test Speakers",
            channels=2,
            samplerate=48000.0,
        )

        with (
            patch.object(Camera, "list_devices", return_value=[camera]),
            patch.object(AudioInput, "list_devices", return_value=[audio_input]),
            patch.object(AudioOutput, "list_devices", return_value=[audio_output]),
            patch(
                "tui.device_setup_screen.launch_camera_preview",
                return_value=CameraPreviewResult(successful=True),
            ) as launch_preview,
        ):
            app = OdiaApp()
            async with app.run_test() as pilot:
                await pilot.pause()
                screen = app.screen
                screen.query_one("#camera", Select).value = camera.index
                await pilot.pause()

                snapshot_button = screen.query_one("#snapshot-camera", Button)
                stream_button = screen.query_one("#stream-camera", Button)
                self.assertFalse(snapshot_button.disabled)
                self.assertFalse(stream_button.disabled)

                await pilot.click("#snapshot-camera")
                await app.workers.wait_for_complete()
                await pilot.pause()
                snapshot_status = str(screen.query_one("#status", Static).content)
                self.assertIn("Snapshot preview closed", snapshot_status)

                await pilot.click("#stream-camera")
                await app.workers.wait_for_complete()
                await pilot.pause()
                stream_status = str(screen.query_one("#status", Static).content)
                self.assertIn("Stream preview closed", stream_status)

        modes = [call.args[1] for call in launch_preview.call_args_list]
        self.assertEqual(
            modes,
            [CameraPreviewMode.SNAPSHOT, CameraPreviewMode.STREAM],
        )

    async def test_microphone_monitor_records_levels_then_plays_back(self) -> None:
        camera = CameraInfo(
            2,
            "Test Camera",
            "/dev/test-camera",
            None,
            None,
            cv2.CAP_ANY,
        )
        audio_input = AudioInputInfo(
            index=7,
            name="Test Microphone",
            channels=1,
            samplerate=16000.0,
        )
        audio_output = AudioOutputInfo(
            index=8,
            name="Test Speakers",
            channels=2,
            samplerate=48000.0,
        )

        def monitor(audio_input, audio_output, stop_event, on_level):
            on_level(-12.0)
            stop_event.wait(timeout=2.0)
            return AudioPreviewResult(
                successful=True,
                duration_seconds=1.5,
                peak_db=-6.0,
            )

        with (
            patch.object(Camera, "list_devices", return_value=[camera]),
            patch.object(AudioInput, "list_devices", return_value=[audio_input]),
            patch.object(AudioOutput, "list_devices", return_value=[audio_output]),
            patch(
                "tui.device_setup_screen.monitor_record_and_play",
                side_effect=monitor,
            ) as live_monitor,
        ):
            app = OdiaApp()
            async with app.run_test() as pilot:
                await pilot.pause()
                screen = app.screen
                screen.query_one("#audio-input", Select).value = audio_input.index
                screen.query_one("#audio-output", Select).value = audio_output.index
                await pilot.pause()

                monitor_button = screen.query_one("#monitor-microphone", Button)
                self.assertFalse(monitor_button.disabled)
                await pilot.click("#monitor-microphone")
                await pilot.pause(0.1)

                level_status = str(screen.query_one("#status", Static).content)
                self.assertIn("안녕하세요", level_status)
                self.assertIn("-12.0 dB", level_status)
                self.assertEqual(str(monitor_button.label), "Done")
                level_bar = screen.query_one("#microphone-level", ProgressBar)
                self.assertTrue(level_bar.display)
                self.assertEqual(level_bar.progress, 48.0)

                await pilot.click("#monitor-microphone")
                await app.workers.wait_for_complete()
                await pilot.pause()
                stopped_status = str(screen.query_one("#status", Static).content)
                self.assertIn("recorded 1.5s, peak -6.0 dB", stopped_status)
                self.assertFalse(level_bar.display)

        live_monitor.assert_called_once()


if __name__ == "__main__":
    unittest.main(verbosity=2)
