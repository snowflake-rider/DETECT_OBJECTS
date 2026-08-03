"""Behavior tests for collecting matched detections into one story session."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest

from PySide6.QtGui import QColor, QImage

from detect_objects.desktop.yolo_detection import Detection
from detect_objects.story.session import SessionRecorder


class SessionRecorderTests(unittest.TestCase):
    def test_matching_detection_creates_snapshot_and_event_document(self) -> None:
        captured_at = datetime(2026, 8, 3, 12, 30, tzinfo=timezone.utc)
        image = QImage(4, 3, QImage.Format.Format_RGB32)
        image.fill(QColor("#336699"))

        with tempfile.TemporaryDirectory() as temporary_directory:
            recorder = SessionRecorder(
                Path(temporary_directory),
                session_id="presentation-demo",
                now=lambda: captured_at,
            )
            recorder.record_instruction("사람을 찾아줘", ("person",))

            event = recorder.record_detection(
                image,
                [
                    Detection(
                        bounds=(0, 0, 3, 2),
                        class_name="person",
                        confidence=0.91,
                    )
                ],
            )

            self.assertIsNotNone(event)
            snapshot_path = recorder.session_dir / event.snapshot
            self.assertTrue(snapshot_path.is_file())
            self.assertEqual(recorder.snapshot_paths, (snapshot_path,))

            document = json.loads(recorder.events_path.read_text(encoding="utf-8"))
            self.assertEqual(document["session_id"], "presentation-demo")
            self.assertEqual(
                document["instructions"],
                [
                    {
                        "timestamp": "2026-08-03T12:30:00+00:00",
                        "text": "사람을 찾아줘",
                        "classes": ["person"],
                    }
                ],
            )
            self.assertEqual(
                document["detections"],
                [
                    {
                        "timestamp": "2026-08-03T12:30:00+00:00",
                        "snapshot": event.snapshot,
                        "objects": [
                            {
                                "class_name": "person",
                                "confidence": 0.91,
                            }
                        ],
                    }
                ],
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
