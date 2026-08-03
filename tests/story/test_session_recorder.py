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
    def test_matching_detection_creates_yolo_box_crop_and_event_document(self) -> None:
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

            events = recorder.record_detection(
                image,
                [
                    Detection(
                        bounds=(0, 0, 3, 2),
                        class_name="person",
                        confidence=0.91,
                    )
                ],
            )

            self.assertEqual(len(events), 1)
            event = events[0]
            crop_path = recorder.session_dir / event.crop
            self.assertTrue(crop_path.is_file())
            self.assertEqual(crop_path.parent.name, "crops")
            crop = QImage(str(crop_path))
            self.assertEqual((crop.width(), crop.height()), (3, 2))
            self.assertEqual(recorder.crop_paths, (crop_path,))
            self.assertEqual(recorder.selected_crop_paths, (crop_path,))

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
                        "crop": event.crop,
                        "selected": True,
                        "objects": [
                            {
                                "class_name": "person",
                                "confidence": 0.91,
                            }
                        ],
                    }
                ],
            )

    def test_crop_can_be_excluded_from_story_or_removed(self) -> None:
        captured_at = datetime(2026, 8, 3, 12, 30, tzinfo=timezone.utc)
        image = QImage(8, 6, QImage.Format.Format_RGB32)
        image.fill(QColor("#336699"))

        with tempfile.TemporaryDirectory() as temporary_directory:
            recorder = SessionRecorder(
                Path(temporary_directory),
                session_id="crop-queue-demo",
                cooldown_seconds=0,
                now=lambda: captured_at,
            )
            recorder.record_instruction("사람을 찾아줘", ("person",))
            event = recorder.record_detection(
                image,
                [Detection((1, 1, 7, 5), "person", 0.91)],
            )[0]
            crop_path = recorder.session_dir / event.crop

            recorder.set_crop_selected(crop_path, False)

            self.assertEqual(recorder.selected_crop_paths, ())
            document = json.loads(recorder.events_path.read_text(encoding="utf-8"))
            self.assertFalse(document["detections"][0]["selected"])

            recorder.remove_crop(crop_path)

            self.assertFalse(crop_path.exists())
            self.assertEqual(recorder.crop_paths, ())
            document = json.loads(recorder.events_path.read_text(encoding="utf-8"))
            self.assertEqual(document["detections"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
