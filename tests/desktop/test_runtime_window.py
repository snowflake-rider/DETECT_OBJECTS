"""Behavior tests for the standalone PySide runtime window."""

from __future__ import annotations

import os
from types import SimpleNamespace
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QFrame, QLabel, QLineEdit, QPushButton

from detect_objects.device_setup.audio import (
    AudioInput,
    AudioInputInfo,
    AudioOutput,
    AudioOutputInfo,
)
from detect_objects.device_setup.camera import Camera
from detect_objects.device_setup.context import Context
from detect_objects.device_setup.environment import Environment
from detect_objects.desktop.fake_video import FakeVideoStream
from detect_objects.desktop.runtime_window import RuntimeWindow
from detect_objects.models.catalog import ModelSelection


class RuntimeWindowTests(unittest.TestCase):
    """Verify the first desktop shell through its visible controls."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.window = RuntimeWindow()
        self.window.show()
        self.application.processEvents()

    def tearDown(self) -> None:
        self.window.close()
        self.application.processEvents()

    def test_window_presents_runtime_dashboard_shell(self) -> None:
        self.assertEqual(self.window.windowTitle(), "ODIA Live")
        video_panel = self.window.findChild(QLabel, "video-panel")
        self.assertIsNotNone(video_panel.pixmap())
        self.assertEqual(
            self.window.findChild(QLabel, "yolo-status").text(),
            "YOLO: Not started",
        )
        self.assertEqual(
            self.window.findChild(QLabel, "whisper-status").text(),
            "Whisper: Not started",
        )
        self.assertIsNotNone(self.window.findChild(QLabel, "transcript"))
        self.assertIsNotNone(self.window.findChild(QLineEdit, "command-input"))
        self.assertIsNotNone(self.window.findChild(QPushButton, "send-command"))
        self.assertIsNotNone(self.window.findChild(QPushButton, "toggle-preview"))
        quit_button = self.window.findChild(QPushButton, "quit-runtime")
        self.assertIsNotNone(quit_button)
        self.assertEqual(quit_button.text(), "Quit")

    def test_window_uses_camera_first_live_lens_layout(self) -> None:
        self.assertIsNotNone(self.window.findChild(QFrame, "top-rail"))
        self.assertIsNotNone(self.window.findChild(QFrame, "command-dock"))
        self.assertEqual(
            self.window.findChild(QLabel, "live-status").text(),
            "● LIVE",
        )
        video_panel = self.window.findChild(QLabel, "video-panel")
        self.assertGreaterEqual(video_panel.minimumWidth(), 640)
        self.assertGreaterEqual(video_panel.minimumHeight(), 360)

    def test_window_shows_devices_and_models_selected_in_setup(self) -> None:
        context = Context(
            environment=Environment("Darwin", "25", "arm64", "3.11"),
            camera=Camera(SimpleNamespace(index=3, name="Studio Camera", backend=1200)),
            audio_input=AudioInput(AudioInputInfo(4, "Studio Microphone", 1, 48000.0)),
            audio_output=AudioOutput(AudioOutputInfo(5, "Studio Speakers", 2, 48000.0)),
            models=ModelSelection(voice_id="whisper_tiny_ko"),
        )
        configured_window = RuntimeWindow(
            context=context,
            video_stream=FakeVideoStream(),
        )
        configured_window.show()
        self.application.processEvents()
        self.addCleanup(configured_window.close)

        self.assertEqual(
            configured_window.findChild(QLabel, "camera-selection").text(),
            "Camera: Studio Camera (index 3)",
        )
        self.assertEqual(
            configured_window.findChild(QLabel, "audio-input-selection").text(),
            "Audio input: Studio Microphone",
        )
        self.assertEqual(
            configured_window.findChild(QLabel, "audio-output-selection").text(),
            "Audio output: Studio Speakers",
        )
        self.assertEqual(
            configured_window.findChild(QLabel, "yolo-status").text(),
            "YOLO: YOLO-World v2 Small · Not started",
        )
        self.assertEqual(
            configured_window.findChild(QLabel, "whisper-status").text(),
            "Whisper: Whisper Tiny — Korean · Not started",
        )

    def test_camera_error_is_shown_without_closing_the_window(self) -> None:
        self.window.show_video_error("Could not open 'Studio Camera'.")

        video_panel = self.window.findChild(QLabel, "video-panel")
        self.assertEqual(
            video_panel.text(),
            "Camera preview unavailable\nCould not open 'Studio Camera'.",
        )
        self.assertTrue(self.window.isVisible())
        self.assertEqual(
            self.window.findChild(QPushButton, "toggle-preview").text(),
            "Resume",
        )

    def test_window_shows_model_and_detection_updates(self) -> None:
        self.window.show_model_status("Ready · Test accelerator")
        self.window.show_detections(2, "PERSON 88% · CUP 76%")

        self.assertEqual(
            self.window.findChild(QLabel, "yolo-status").text(),
            "YOLO: Ready · Test accelerator",
        )
        self.assertEqual(
            self.window.findChild(QLabel, "detection-count").text(),
            "2 objects",
        )
        self.assertEqual(
            self.window.findChild(QLabel, "detection-summary").text(),
            "PERSON 88% · CUP 76%",
        )

    def test_video_preview_scales_with_its_aspect_ratio(self) -> None:
        video_panel = self.window.findChild(QLabel, "video-panel")
        pixmap = video_panel.pixmap()

        self.assertLessEqual(pixmap.width(), video_panel.width())
        self.assertLessEqual(pixmap.height(), video_panel.height())
        self.assertAlmostEqual(pixmap.width() / pixmap.height(), 16 / 9, places=1)

    def test_user_can_pause_and_restart_the_preview(self) -> None:
        toggle = self.window.findChild(QPushButton, "toggle-preview")
        self.assertTrue(self.window.video_stream.is_running)

        QTest.mouseClick(toggle, Qt.MouseButton.LeftButton)
        self.application.processEvents()

        self.assertFalse(self.window.video_stream.is_running)
        self.assertEqual(toggle.text(), "Resume")

        QTest.mouseClick(toggle, Qt.MouseButton.LeftButton)
        self.application.processEvents()

        self.assertTrue(self.window.video_stream.is_running)
        self.assertEqual(toggle.text(), "Pause")

    def test_user_can_submit_a_typed_command(self) -> None:
        commands: list[str] = []
        self.window.command_submitted.connect(commands.append)
        command_input = self.window.findChild(QLineEdit, "command-input")
        command_input.setText("사람을 찾아줘")

        QTest.mouseClick(
            self.window.findChild(QPushButton, "send-command"),
            Qt.MouseButton.LeftButton,
        )
        self.application.processEvents()

        self.assertEqual(commands, ["사람을 찾아줘"])
        self.assertEqual(command_input.text(), "")
        self.assertEqual(
            self.window.findChild(QLabel, "transcript").text(),
            "Typed command: 사람을 찾아줘",
        )

    def test_quit_button_requests_shutdown_and_closes_window(self) -> None:
        quit_requests: list[bool] = []
        self.window.quit_requested.connect(lambda: quit_requests.append(True))

        QTest.mouseClick(
            self.window.findChild(QPushButton, "quit-runtime"),
            Qt.MouseButton.LeftButton,
        )
        self.application.processEvents()

        self.assertEqual(quit_requests, [True])
        self.assertFalse(self.window.isVisible())
        self.assertFalse(self.window.video_stream.is_running)


if __name__ == "__main__":
    unittest.main(verbosity=2)
