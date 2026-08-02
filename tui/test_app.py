"""Headless tests for the Textual application flow."""

from __future__ import annotations

import unittest
from unittest.mock import patch

import cv2
from cv2_enumerate_cameras.camera_info import CameraInfo
from textual.widgets import Button, Select

from device_setup import Audio, AudioInfo, Camera, Context
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
        microphone = AudioInfo(
            index=7,
            name="Test Microphone",
            channels=1,
            samplerate=16000.0,
        )

        with (
            patch.object(
                Camera,
                "list_devices",
                return_value=[camera],
            ),
            patch.object(
                Audio,
                "list_devices",
                return_value=[microphone],
            ),
        ):
            app = OdiaApp()
            async with app.run_test() as pilot:
                await pilot.pause()
                screen = app.screen
                continue_button = screen.query_one("#continue", Button)
                self.assertTrue(continue_button.disabled)

                screen.query_one("#camera", Select).value = camera.index
                screen.query_one("#microphone", Select).value = microphone.index
                await pilot.pause()

                self.assertFalse(continue_button.disabled)
                await pilot.click("#continue")
                await pilot.pause()

        context = app.return_value
        self.assertIsInstance(context, Context)
        self.assertIs(context.camera.info, camera)
        self.assertIs(context.audio.info, microphone)


if __name__ == "__main__":
    unittest.main(verbosity=2)
