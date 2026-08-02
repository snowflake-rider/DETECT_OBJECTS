"""Tests for streaming a selected camera into the PySide interface."""

from __future__ import annotations

import os
import time
import unittest

import numpy as np

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QColor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from detect_objects.desktop.camera_video import CameraVideoStream
from detect_objects.desktop.yolo_detection import Detection


class MemoryCapture:
    """Small in-memory replacement for the external OpenCV camera boundary."""

    def __init__(self, frame: np.ndarray, *, opened: bool = True) -> None:
        self.frame = frame
        self.opened = opened
        self.released = False

    def isOpened(self) -> bool:
        return self.opened

    def read(self):
        time.sleep(0.005)
        return True, self.frame.copy()

    def release(self) -> None:
        self.released = True


class RecordingCaptureFactory:
    def __init__(self, capture: MemoryCapture) -> None:
        self.capture = capture
        self.calls: list[tuple[int, int]] = []

    def __call__(self, index: int, backend: int) -> MemoryCapture:
        self.calls.append((index, backend))
        return self.capture


class MemoryDetector:
    """In-memory boundary used instead of loading model weights in this test."""

    device_name = "Test accelerator"

    def __init__(self) -> None:
        self.loaded = False
        self.closed = False
        self.processed_frames = 0

    def load(self) -> None:
        self.loaded = True

    def process(self, frame: np.ndarray):
        self.processed_frames += 1
        return frame, [
            Detection(
                bounds=(0, 0, 1, 1),
                class_name="person",
                confidence=0.876,
            )
        ]

    def close(self) -> None:
        self.closed = True


class CameraVideoStreamTests(unittest.TestCase):
    """Verify frames and cleanup at the real-camera stream boundary."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    @staticmethod
    def wait_until(condition, timeout: float = 2.0) -> None:
        deadline = time.monotonic() + timeout
        while not condition() and time.monotonic() < deadline:
            QTest.qWait(20)

    def test_selected_camera_emits_frames_and_releases_capture(self) -> None:
        capture = MemoryCapture(
            np.array([[[255, 0, 0]]], dtype=np.uint8),
        )
        capture_factory = RecordingCaptureFactory(capture)
        received_frames = []
        stream = CameraVideoStream(
            index=3,
            backend=1200,
            name="Studio Camera",
            capture_factory=capture_factory,
        )
        stream.frame_ready.connect(lambda image: received_frames.append(image))

        stream.start()
        self.wait_until(lambda: bool(received_frames))
        stream.stop()
        self.application.processEvents()

        self.assertEqual(capture_factory.calls, [(3, 1200)])
        self.assertGreaterEqual(len(received_frames), 1)
        self.assertEqual(received_frames[0].pixelColor(0, 0), QColor(0, 0, 255))
        self.assertTrue(capture.released)
        self.assertFalse(stream.is_running)

    def test_detector_runs_in_stream_and_reports_percentage_summary(self) -> None:
        capture = MemoryCapture(np.zeros((4, 4, 3), dtype=np.uint8))
        detector = MemoryDetector()
        model_statuses = []
        detection_summaries = []
        stream = CameraVideoStream(
            index=3,
            backend=1200,
            name="Studio Camera",
            capture_factory=RecordingCaptureFactory(capture),
            detector=detector,
        )
        stream.model_status.connect(lambda status: model_statuses.append(status))
        stream.detections_ready.connect(
            lambda count, summary: detection_summaries.append((count, summary))
        )

        stream.start()
        self.wait_until(lambda: detector.processed_frames >= 1)
        stream.stop()
        self.application.processEvents()

        self.assertTrue(detector.loaded)
        self.assertGreaterEqual(detector.processed_frames, 1)
        self.assertTrue(detector.closed)
        self.assertIn("Ready · Test accelerator", model_statuses)
        self.assertIn((1, "PERSON 88%"), detection_summaries)


if __name__ == "__main__":
    unittest.main(verbosity=2)
