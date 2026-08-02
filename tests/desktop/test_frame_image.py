"""Tests for converting OpenCV frames into Qt images."""

from __future__ import annotations

import os
import unittest

import numpy as np

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QColor

from detect_objects.desktop.frame_image import frame_to_qimage


class FrameImageTests(unittest.TestCase):
    """Verify color order and ownership at the OpenCV-to-Qt boundary."""

    def test_bgr_frame_becomes_an_independent_qimage(self) -> None:
        frame = np.array(
            [[[255, 0, 0], [0, 0, 255]]],
            dtype=np.uint8,
        )

        image = frame_to_qimage(frame)
        frame[:] = 0

        self.assertEqual(image.size().width(), 2)
        self.assertEqual(image.size().height(), 1)
        self.assertEqual(image.pixelColor(0, 0), QColor(0, 0, 255))
        self.assertEqual(image.pixelColor(1, 0), QColor(255, 0, 0))


if __name__ == "__main__":
    unittest.main(verbosity=2)
