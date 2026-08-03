"""End-to-end Desktop behavior for collecting and generating a session story."""

from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
import tempfile
import time
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QLineEdit, QPushButton

from detect_objects.desktop.fake_video import FakeVideoStream
from detect_objects.desktop.runtime_window import RuntimeWindow
from detect_objects.desktop.yolo_detection import Detection
from detect_objects.story.generator import StoryResult
from detect_objects.story.session import SessionRecorder


class RecordingStoryGenerator:
    def __init__(self, representative_image: Path) -> None:
        self.representative_image = representative_image
        self.sessions: list[Path] = []

    def generate(self, session_dir: Path) -> StoryResult:
        self.sessions.append(session_dir)
        return StoryResult(
            title="The Person in the Blue Frame",
            story="A curious person appeared, right when ODIA was asked to look.",
            representative_image=self.representative_image,
        )


class StoryIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    @staticmethod
    def wait_until(condition, timeout: float = 2.0) -> None:
        deadline = time.monotonic() + timeout
        while not condition() and time.monotonic() < deadline:
            QTest.qWait(20)

    def test_story_button_uses_snapshots_collected_after_instruction(self) -> None:
        captured_at = datetime(2026, 8, 3, 15, 0, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as temporary_directory:
            recorder = SessionRecorder(
                Path(temporary_directory),
                session_id="desktop-demo",
                now=lambda: captured_at,
            )
            expected_image = (
                recorder.session_dir
                / "snapshots"
                / ("20260803T150000000000-person.png")
            )
            generator = RecordingStoryGenerator(expected_image)
            video_stream = FakeVideoStream()
            window = RuntimeWindow(
                video_stream=video_stream,
                session_recorder=recorder,
                story_generator=generator,
            )
            window.show()
            self.addCleanup(window.close)
            self.application.processEvents()

            command_input = window.findChild(QLineEdit, "command-input")
            command_input.setText("사람을 찾아줘")
            QTest.mouseClick(
                window.findChild(QPushButton, "send-command"),
                Qt.MouseButton.LeftButton,
            )

            image = QImage(8, 6, QImage.Format.Format_RGB32)
            image.fill(QColor("#245c82"))
            video_stream.detection_frame_ready.emit(
                image,
                [
                    Detection(
                        bounds=(0, 0, 7, 5),
                        class_name="person",
                        confidence=0.94,
                    )
                ],
            )
            self.application.processEvents()
            self.assertTrue(expected_image.is_file())

            story_button = window.findChild(QPushButton, "generate-story")
            QTest.mouseClick(story_button, Qt.MouseButton.LeftButton)
            self.wait_until(
                lambda: "The Person in the Blue Frame"
                in window.findChild(QLabel, "story-output").text()
            )

            self.assertEqual(generator.sessions, [recorder.session_dir])
            self.assertIn(
                "A curious person appeared",
                window.findChild(QLabel, "story-output").text(),
            )
            self.assertFalse(window.findChild(QLabel, "story-image").pixmap().isNull())
            self.assertTrue(story_button.isEnabled())


if __name__ == "__main__":
    unittest.main(verbosity=2)
