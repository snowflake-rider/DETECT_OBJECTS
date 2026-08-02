"""Tests for presenting YOLO detections in the desktop camera feed."""

from __future__ import annotations

import unittest

import numpy as np
import torch
from ultralytics.engine.results import Boxes

from detect_objects.desktop.yolo_detection import (
    DETECTION_COLOR,
    Detection,
    YoloDetector,
    detections_from_boxes,
    draw_detections,
    format_detection_label,
)


class YoloDetectionTests(unittest.TestCase):
    def test_confidence_is_displayed_as_a_whole_percentage(self) -> None:
        self.assertEqual(format_detection_label("person", 0.876), "PERSON 88%")

    def test_detection_box_is_drawn_without_changing_source_frame(self) -> None:
        source = np.zeros((60, 80, 3), dtype=np.uint8)
        detection = Detection(
            bounds=(10, 10, 40, 40),
            class_name="person",
            confidence=0.876,
        )

        annotated = draw_detections(source, [detection])

        self.assertFalse(np.any(source))
        self.assertEqual(tuple(annotated[40, 10]), DETECTION_COLOR)
        self.assertTrue(np.any(annotated))

    def test_yolo_box_becomes_a_desktop_detection(self) -> None:
        boxes = Boxes(
            torch.tensor([[10.0, 20.0, 50.0, 60.0, 0.876, 0.0]]),
            orig_shape=(100, 100),
        )

        detections = detections_from_boxes(boxes, {0: "person"})

        self.assertEqual(len(detections), 1)
        self.assertEqual(detections[0].bounds, (10, 20, 50, 60))
        self.assertEqual(detections[0].class_name, "person")
        self.assertAlmostEqual(detections[0].confidence, 0.876, places=3)

    def test_detector_loads_predicts_and_closes_selected_model(self) -> None:
        boxes = Boxes(
            torch.tensor([[10.0, 20.0, 50.0, 60.0, 0.876, 0.0]]),
            orig_shape=(100, 100),
        )

        class MemoryVisionManager:
            device_name = "Test accelerator"

            def __init__(self) -> None:
                self.loaded = False
                self.cached_classes = None
                self.active_classes = None
                self.closed = False

            def load(self) -> None:
                self.loaded = True

            def cache_class_embeddings(self, classes) -> None:
                self.cached_classes = tuple(classes)

            def activate_cached_classes(self, classes) -> None:
                self.active_classes = tuple(classes)

            def predict(self, frame):
                return boxes, {0: "person"}

            def close(self) -> None:
                self.closed = True

        manager = MemoryVisionManager()
        selected_models = []
        detector = YoloDetector(
            "selected-yolo",
            manager_factory=lambda model_id: (
                selected_models.append(model_id) or manager
            ),
        )

        detector.load()
        annotated, detections = detector.process(
            np.zeros((100, 100, 3), dtype=np.uint8)
        )
        device_name = detector.device_name
        detector.close()

        self.assertEqual(selected_models, ["selected-yolo"])
        self.assertTrue(manager.loaded)
        self.assertIn("person", manager.cached_classes)
        self.assertEqual(
            manager.active_classes, ("cell phone", "clock", "keyboard", "person")
        )
        self.assertEqual(device_name, "Test accelerator")
        self.assertEqual(len(detections), 1)
        self.assertTrue(np.any(annotated))
        self.assertTrue(manager.closed)


if __name__ == "__main__":
    unittest.main(verbosity=2)
