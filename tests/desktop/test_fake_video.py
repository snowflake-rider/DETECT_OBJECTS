"""Tests for the hardware-free desktop video stream."""

from __future__ import annotations

from datetime import datetime
import os
import unittest

import numpy as np

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from detect_objects.desktop.fake_video import FakeVideoStream, create_fake_frame


class FakeVideoTests(unittest.TestCase):
    """Verify deterministic frames and timer lifecycle behavior."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    def test_frame_has_expected_shape_and_animation(self) -> None:
        timestamp = datetime(2026, 8, 2, 12, 30, 45)

        first = create_fake_frame(0, width=320, height=180, timestamp=timestamp)
        later = create_fake_frame(4, width=320, height=180, timestamp=timestamp)

        self.assertEqual(first.shape, (180, 320, 3))
        self.assertEqual(first.dtype, np.uint8)
        self.assertFalse(np.array_equal(first, later))

    def test_stream_emits_frames_until_stopped(self) -> None:
        stream = FakeVideoStream(fps=20)
        received_frames = []
        stream.frame_ready.connect(received_frames.append)

        stream.start()
        QTest.qWait(130)

        self.assertTrue(stream.is_running)
        self.assertGreaterEqual(len(received_frames), 2)
        self.assertGreaterEqual(stream.frame_number, 2)

        stream.stop()
        count_after_stop = len(received_frames)
        QTest.qWait(100)

        self.assertFalse(stream.is_running)
        self.assertEqual(len(received_frames), count_after_stop)


if __name__ == "__main__":
    unittest.main(verbosity=2)
