"""Behavior tests for the standalone PySide runtime window."""

from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QLineEdit, QPushButton

from detect_objects.desktop.runtime_window import RuntimeWindow


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
        self.assertEqual(self.window.windowTitle(), "ODIA Desktop")
        self.assertIn(
            "Camera preview",
            self.window.findChild(QLabel, "video-panel").text(),
        )
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
        self.assertIsNotNone(self.window.findChild(QPushButton, "stop-runtime"))

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

    def test_stop_button_requests_shutdown_and_closes_window(self) -> None:
        stop_requests: list[bool] = []
        self.window.stop_requested.connect(lambda: stop_requests.append(True))

        QTest.mouseClick(
            self.window.findChild(QPushButton, "stop-runtime"),
            Qt.MouseButton.LeftButton,
        )
        self.application.processEvents()

        self.assertEqual(stop_requests, [True])
        self.assertFalse(self.window.isVisible())


if __name__ == "__main__":
    unittest.main(verbosity=2)
