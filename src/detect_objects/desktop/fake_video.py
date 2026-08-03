"""Synthetic video frames for testing the isolated desktop interface."""

from __future__ import annotations

from datetime import datetime

import cv2
import numpy as np
from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QImage

from .frame_image import frame_to_qimage


def create_fake_frame(
    frame_number: int,
    *,
    width: int = 640,
    height: int = 360,
    timestamp: datetime | None = None,
) -> np.ndarray:
    """Draw one BGR test frame without opening a camera or loading a model."""
    if width <= 0 or height <= 0:
        raise ValueError("frame width and height must be greater than zero")

    frame = np.full((height, width, 3), (22, 18, 14), dtype=np.uint8)
    frame[:, :, 0] += np.linspace(0, 30, width, dtype=np.uint8)

    radius = max(6, min(width, height) // 12)
    travel = max(1, width - (2 * radius))
    center_x = radius + ((frame_number * 8) % travel)
    center_y = height // 2
    cv2.circle(frame, (center_x, center_y), radius, (84, 180, 255), -1)

    shown_time = timestamp or datetime.now()
    cv2.putText(
        frame,
        "ODIA DESKTOP PREVIEW",
        (20, 38),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (235, 238, 244),
        2,
        cv2.LINE_AA,
    )
    cv2.putText(
        frame,
        f"Frame {frame_number:05d}",
        (20, height - 48),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (210, 216, 226),
        1,
        cv2.LINE_AA,
    )
    cv2.putText(
        frame,
        shown_time.strftime("%H:%M:%S.%f")[:-3],
        (20, height - 20),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (160, 170, 188),
        1,
        cv2.LINE_AA,
    )
    return frame


class FakeVideoStream(QObject):
    """Emit synthetic Qt images at a small, UI-friendly frame rate."""

    frame_ready = Signal(QImage)
    error = Signal(str)
    model_status = Signal(str)
    detections_ready = Signal(int, str)
    keyword_queue_changed = Signal(object)
    active_classes_changed = Signal(object)

    def __init__(self, *, fps: int = 12, parent: QObject | None = None) -> None:
        super().__init__(parent)
        if fps <= 0:
            raise ValueError("fps must be greater than zero")

        self._frame_number = 0
        self._pending_classes: tuple[str, ...] | None = None
        self._timer = QTimer(self)
        self._timer.setInterval(max(1, round(1000 / fps)))
        self._timer.timeout.connect(self._emit_frame)

    @property
    def frame_number(self) -> int:
        """Return the number assigned to the next frame."""
        return self._frame_number

    @property
    def is_running(self) -> bool:
        """Return whether the timer is currently producing frames."""
        return self._timer.isActive()

    @property
    def pending_classes(self) -> tuple[str, ...] | None:
        """Return the keyword batch waiting for the next synthetic frame."""
        return self._pending_classes

    def start(self) -> None:
        """Begin emitting frames, including one immediately."""
        if self.is_running:
            return
        self._emit_frame()
        self._timer.start()

    def stop(self) -> None:
        """Stop producing new frames."""
        self._timer.stop()

    def set_classes(self, classes: tuple[str, ...]) -> None:
        """Accept instruction updates when the UI uses its synthetic preview."""
        if not classes:
            return
        self._pending_classes = classes
        self.keyword_queue_changed.emit(classes)

    def _emit_frame(self) -> None:
        if self._pending_classes is not None:
            active_classes = self._pending_classes
            self._pending_classes = None
            self.keyword_queue_changed.emit(())
            self.active_classes_changed.emit(active_classes)

        frame = create_fake_frame(self._frame_number)
        self._frame_number += 1
        self.frame_ready.emit(frame_to_qimage(frame))
