"""Tests for the isolated OpenCV camera preview adapter."""

from __future__ import annotations

import subprocess
import unittest
from unittest.mock import patch

import cv2
from cv2_enumerate_cameras.camera_info import CameraInfo

from detect_objects.device_setup import Camera
from detect_objects.opencv_preview.camera_preview import (
    CameraPreviewMode,
    launch_camera_preview,
    show_camera_preview,
)


class FakeCapture:
    """Simulate the OpenCV capture methods used by the preview."""

    def __init__(self, opened: bool = True) -> None:
        self.opened = opened
        self.frame = object()
        self.released = False

    def isOpened(self) -> bool:
        return self.opened

    def read(self) -> tuple[bool, object]:
        return True, self.frame

    def release(self) -> None:
        self.released = True


class CameraPreviewTests(unittest.TestCase):
    """Verify preview cleanup and child-process launching."""

    def setUp(self) -> None:
        info = CameraInfo(
            2,
            "Test Camera",
            "/dev/test-camera",
            None,
            None,
            cv2.CAP_ANY,
        )
        self.camera = Camera(info)

    def test_snapshot_displays_one_frame_and_releases_camera(self) -> None:
        capture = FakeCapture()
        with (
            patch(
                "detect_objects.opencv_preview.camera_preview.cv2.VideoCapture",
                return_value=capture,
            ),
            patch("detect_objects.opencv_preview.camera_preview.cv2.imshow") as imshow,
            patch(
                "detect_objects.opencv_preview.camera_preview.cv2.waitKey",
                return_value=ord("q"),
            ),
            patch(
                "detect_objects.opencv_preview.camera_preview.cv2.destroyAllWindows"
            ) as destroy,
        ):
            result = show_camera_preview(
                index=2,
                backend=cv2.CAP_ANY,
                name="Test Camera",
                mode=CameraPreviewMode.SNAPSHOT,
            )

        self.assertTrue(result.successful)
        imshow.assert_called_once_with(
            "Test Camera — Snapshot Preview — " "Press Q or Escape to return to TUI",
            capture.frame,
        )
        self.assertTrue(capture.released)
        destroy.assert_called_once()

    def test_stream_displays_frames_until_user_quits(self) -> None:
        capture = FakeCapture()
        with (
            patch(
                "detect_objects.opencv_preview.camera_preview.cv2.VideoCapture",
                return_value=capture,
            ),
            patch("detect_objects.opencv_preview.camera_preview.cv2.imshow") as imshow,
            patch(
                "detect_objects.opencv_preview.camera_preview.cv2.waitKey",
                return_value=ord("q"),
            ),
            patch("detect_objects.opencv_preview.camera_preview.cv2.destroyAllWindows"),
        ):
            result = show_camera_preview(
                index=2,
                backend=cv2.CAP_ANY,
                name="Test Camera",
                mode=CameraPreviewMode.STREAM,
            )

        self.assertTrue(result.successful)
        imshow.assert_called_once_with(
            "Test Camera — Stream Preview — " "Press Q or Escape to return to TUI",
            capture.frame,
        )
        self.assertTrue(capture.released)

    def test_launcher_passes_camera_and_mode_to_child_process(self) -> None:
        completed = subprocess.CompletedProcess([], returncode=0)
        with patch(
            "detect_objects.opencv_preview.camera_preview.subprocess.run",
            return_value=completed,
        ) as run:
            result = launch_camera_preview(
                self.camera,
                CameraPreviewMode.STREAM,
            )

        self.assertTrue(result.successful)
        command = run.call_args.args[0]
        self.assertIn("detect_objects.opencv_preview.camera_preview", command)
        self.assertIn("2", command)
        self.assertIn("stream", command)


if __name__ == "__main__":
    unittest.main(verbosity=2)
