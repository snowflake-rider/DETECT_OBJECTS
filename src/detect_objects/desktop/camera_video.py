"""Read a selected OpenCV camera without blocking the PySide interface."""

from __future__ import annotations

from collections.abc import Callable
from threading import Event
from typing import Protocol

import cv2
import numpy as np
from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtGui import QImage

from .frame_image import frame_to_qimage
from .yolo_detection import Detection, format_detection_label


class VideoCapture(Protocol):
    """The small part of ``cv2.VideoCapture`` used by this stream."""

    def isOpened(self) -> bool: ...

    def read(self) -> tuple[bool, np.ndarray | None]: ...

    def release(self) -> None: ...


CaptureFactory = Callable[[int, int], VideoCapture]


class FrameDetector(Protocol):
    """Detection lifecycle used by the camera worker."""

    @property
    def device_name(self) -> str: ...

    def load(self) -> None: ...

    def process(self, frame: np.ndarray) -> tuple[np.ndarray, list[Detection]]: ...

    def close(self) -> None: ...


class CameraVideoStream(QThread):
    """Emit frames from one selected camera on a background Qt thread."""

    frame_ready = Signal(QImage)
    error = Signal(str)
    model_status = Signal(str)
    detections_ready = Signal(int, str)

    def __init__(
        self,
        *,
        index: int,
        backend: int,
        name: str,
        capture_factory: CaptureFactory | None = None,
        detector: FrameDetector | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._index = index
        self._backend = backend
        self._name = name
        self._capture_factory = capture_factory or cv2.VideoCapture
        self._detector = detector
        self._stop_requested = Event()

    @property
    def is_running(self) -> bool:
        """Return whether the capture thread is currently active."""
        return self.isRunning()

    def start(self) -> None:
        """Start reading the selected camera."""
        if self.is_running:
            return
        self._stop_requested.clear()
        super().start()

    def stop(self) -> None:
        """Ask the capture loop to finish and wait for camera cleanup."""
        self._stop_requested.set()
        if self.is_running and QThread.currentThread() is not self:
            self.wait()

    def run(self) -> None:
        """Own the OpenCV capture until stopped or a camera error occurs."""
        capture: VideoCapture | None = None
        try:
            if self._detector is not None:
                self.model_status.emit("Loading…")
                self._detector.load()
                self.model_status.emit(f"Ready · {self._detector.device_name}")

            capture = self._capture_factory(self._index, self._backend)
            if not capture.isOpened():
                self.error.emit(f"Could not open '{self._name}'.")
                return

            while not self._stop_requested.is_set():
                success, frame = capture.read()
                if not success or frame is None:
                    if not self._stop_requested.is_set():
                        self.error.emit("Camera stopped providing frames.")
                    return

                if self._detector is not None:
                    frame, detections = self._detector.process(frame)
                    summary = " · ".join(
                        format_detection_label(
                            detection.class_name,
                            detection.confidence,
                        )
                        for detection in detections[:3]
                    )
                    self.detections_ready.emit(
                        len(detections),
                        summary or "No objects",
                    )
                self.frame_ready.emit(frame_to_qimage(frame))
        except (cv2.error, OSError, RuntimeError, TypeError, ValueError) as error:
            self.error.emit(f"Desktop preview failed: {error}")
        finally:
            if capture is not None:
                capture.release()
            if self._detector is not None:
                self._detector.close()
