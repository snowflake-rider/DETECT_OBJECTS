"""End-to-end Desktop behavior for collecting and generating a session story."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
import time
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
)

from detect_objects.desktop.fake_video import FakeVideoStream
from detect_objects.desktop.runtime_window import RuntimeWindow
from detect_objects.desktop.yolo_detection import Detection
from detect_objects.story.generator import StoryResult
from detect_objects.story.session import SessionRecorder


class RecordingStoryGenerator:
    def __init__(self) -> None:
        self.sessions: list[Path] = []
        self.selected_crops: list[Path] = []

    def generate(self, session_dir: Path) -> StoryResult:
        self.sessions.append(session_dir)
        events = json.loads((session_dir / "events.json").read_text(encoding="utf-8"))
        self.selected_crops = [
            session_dir / event["crop"]
            for event in events["detections"]
            if event["selected"]
        ]
        return StoryResult(
            title="The Person in the Blue Frame",
            story="A curious person appeared, right when ODIA was asked to look.",
            representative_image=self.selected_crops[0],
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

    def test_story_button_uses_only_selected_crops_after_instruction(self) -> None:
        captured_at = datetime(2026, 8, 3, 15, 0, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as temporary_directory:
            recorder = SessionRecorder(
                Path(temporary_directory),
                session_id="desktop-demo",
                now=lambda: captured_at,
            )
            generator = RecordingStoryGenerator()
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
                        bounds=(0, 0, 4, 6),
                        class_name="person",
                        confidence=0.94,
                    ),
                    Detection(
                        bounds=(4, 0, 8, 6),
                        class_name="person",
                        confidence=0.88,
                    ),
                ],
            )
            self.application.processEvents()
            self.assertEqual(len(recorder.crop_paths), 2)
            expected_image = recorder.crop_paths[0]
            excluded_image = recorder.crop_paths[1]
            gallery = window.findChild(QListWidget, "crop-gallery")
            self.assertEqual(gallery.count(), 2)
            gallery.item(1).setCheckState(Qt.CheckState.Unchecked)
            self.application.processEvents()
            self.assertEqual(
                window.findChild(QLabel, "crop-queue-status").text(),
                "1 of 2 crops queued for Codex",
            )

            story_button = window.findChild(QPushButton, "generate-story")
            gallery.item(0).setCheckState(Qt.CheckState.Unchecked)
            self.application.processEvents()
            QTest.mouseClick(story_button, Qt.MouseButton.LeftButton)
            self.application.processEvents()
            self.assertEqual(generator.sessions, [])
            self.assertIn(
                "Select at least one object crop",
                window.findChild(QLabel, "story-output").text(),
            )

            gallery.item(0).setCheckState(Qt.CheckState.Checked)
            self.application.processEvents()
            QTest.mouseClick(story_button, Qt.MouseButton.LeftButton)
            self.wait_until(
                lambda: "The Person in the Blue Frame"
                in window.findChild(QLabel, "story-output").text()
            )

            self.assertEqual(generator.sessions, [recorder.session_dir])
            self.assertEqual(generator.selected_crops, [expected_image])
            self.assertNotIn(excluded_image, generator.selected_crops)
            self.assertIn(
                "A curious person appeared",
                window.findChild(QLabel, "story-output").text(),
            )
            self.assertFalse(window.findChild(QLabel, "story-image").pixmap().isNull())
            self.assertTrue(story_button.isEnabled())

    def test_user_can_open_and_remove_a_detected_crop_in_the_sidebar(self) -> None:
        captured_at = datetime(2026, 8, 3, 15, 0, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as temporary_directory:
            recorder = SessionRecorder(
                Path(temporary_directory),
                session_id="crop-gallery-demo",
                now=lambda: captured_at,
            )
            window = RuntimeWindow(
                video_stream=FakeVideoStream(),
                session_recorder=recorder,
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

            image = QImage(16, 12, QImage.Format.Format_RGB32)
            image.fill(QColor("#245c82"))
            window.video_stream.detection_frame_ready.emit(
                image,
                [
                    Detection(
                        bounds=(0, 0, 15, 11),
                        class_name="person",
                        confidence=0.94,
                    )
                ],
            )
            self.application.processEvents()

            gallery = window.findChild(QListWidget, "crop-gallery")
            self.assertEqual(gallery.count(), 1)
            self.assertIn("PERSON", gallery.item(0).text())

            QTest.mouseClick(
                gallery.viewport(),
                Qt.MouseButton.LeftButton,
                pos=gallery.visualItemRect(gallery.item(0)).center(),
            )
            self.application.processEvents()

            preview = window.findChild(QLabel, "crop-preview")
            details = window.findChild(QLabel, "crop-details")
            self.assertFalse(preview.pixmap().isNull())
            self.assertIn("PERSON 94%", details.text())
            self.assertIn("2026-08-03 15:00:00 UTC", details.text())

            crop_path = recorder.crop_paths[0]
            remove_button = window.findChild(QPushButton, "remove-crop")
            self.assertTrue(remove_button.isEnabled())
            QTest.mouseClick(remove_button, Qt.MouseButton.LeftButton)
            self.application.processEvents()

            self.assertEqual(gallery.count(), 0)
            self.assertFalse(crop_path.exists())
            self.assertEqual(recorder.crop_paths, ())
            self.assertIn("No object crop selected", preview.text())
            self.assertEqual(
                window.findChild(QLabel, "crop-queue-status").text(),
                "0 of 0 crops queued for Codex",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
