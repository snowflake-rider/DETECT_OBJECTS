"""Behavior tests for the Classic OpenCV detection preview."""

from __future__ import annotations

from threading import Event
import unittest
from unittest.mock import MagicMock, patch

import numpy as np

from detect_objects.camera_cv.camera_cv import Camera_Manager


class ClassicCameraManagerTests(unittest.TestCase):
    def test_closing_camera_window_stops_classic_runtime(self) -> None:
        capture = MagicMock()
        capture.isOpened.return_value = True
        capture.read.side_effect = [
            (True, np.zeros((32, 32, 3), dtype=np.uint8)),
            AssertionError("Classic runtime read another frame after window closed"),
        ]
        vision_manager = MagicMock()
        vision_manager.predict.return_value = ([], {})
        shutdown_event = Event()

        with (
            patch(
                "detect_objects.camera_cv.camera_cv.cv2.VideoCapture",
                return_value=capture,
            ),
            patch(
                "detect_objects.camera_cv.camera_cv.create_vision_manager",
                return_value=vision_manager,
            ),
            patch("detect_objects.camera_cv.camera_cv.cv2.imshow"),
            patch(
                "detect_objects.camera_cv.camera_cv.cv2.waitKey",
                return_value=-1,
            ),
            patch(
                "detect_objects.camera_cv.camera_cv.cv2.getWindowProperty",
                return_value=0.0,
            ),
            patch("detect_objects.camera_cv.camera_cv.cv2.destroyAllWindows"),
        ):
            manager = Camera_Manager(
                0,
                thread_event=shutdown_event,
                camera_backend=100,
            )
            manager.load_model()
            manager.start_record()

        self.assertTrue(shutdown_event.is_set())
        capture.release.assert_called()

    def test_lowercase_q_stops_classic_runtime(self) -> None:
        capture = MagicMock()
        capture.isOpened.return_value = True
        capture.read.return_value = (
            True,
            np.zeros((32, 32, 3), dtype=np.uint8),
        )
        vision_manager = MagicMock()
        vision_manager.predict.return_value = ([], {})
        shutdown_event = Event()

        with (
            patch(
                "detect_objects.camera_cv.camera_cv.cv2.VideoCapture",
                return_value=capture,
            ),
            patch(
                "detect_objects.camera_cv.camera_cv.create_vision_manager",
                return_value=vision_manager,
            ),
            patch("detect_objects.camera_cv.camera_cv.cv2.imshow"),
            patch(
                "detect_objects.camera_cv.camera_cv.cv2.waitKey",
                return_value=ord("q"),
            ),
            patch(
                "detect_objects.camera_cv.camera_cv.cv2.getWindowProperty"
            ) as visible,
            patch("detect_objects.camera_cv.camera_cv.cv2.destroyAllWindows"),
        ):
            manager = Camera_Manager(
                0,
                thread_event=shutdown_event,
                camera_backend=100,
            )
            manager.load_model()
            manager.start_record()

        self.assertTrue(shutdown_event.is_set())
        visible.assert_not_called()
        capture.release.assert_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
