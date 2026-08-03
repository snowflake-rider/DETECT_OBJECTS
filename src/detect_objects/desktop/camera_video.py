"""Read a selected OpenCV camera without blocking the PySide interface."""

from __future__ import annotations

from collections.abc import Callable
from queue import Empty, Full, Queue
from threading import Event, Lock
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

    def set_classes(self, classes: tuple[str, ...]) -> None: ...

    def process(self, frame: np.ndarray) -> tuple[np.ndarray, list[Detection]]: ...

    def close(self) -> None: ...


class CameraVideoStream(QThread):
    """Emit frames from one selected camera on a background Qt thread."""

    frame_ready = Signal(QImage)
    error = Signal(str)
    model_status = Signal(str)
    detections_ready = Signal(int, str)
    keyword_queue_changed = Signal(object)
    active_classes_changed = Signal(object)
    detection_frame_ready = Signal(QImage, object)

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
        self._pending_classes: Queue[tuple[str, ...]] = Queue(maxsize=1)
        self._pending_classes_lock = Lock()
        self._pending_classes_snapshot: tuple[str, ...] | None = None

    @property
    def pending_classes(self) -> tuple[str, ...] | None:
        """Return the keyword batch waiting for the camera worker."""
        with self._pending_classes_lock:
            return self._pending_classes_snapshot

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

    def set_classes(self, classes: tuple[str, ...]) -> None:
        """Schedule the latest requested detection classes for the worker."""
        if not classes:
            return

        with self._pending_classes_lock:
            try:
                self._pending_classes.put_nowait(classes)
            except Full:
                try:
                    self._pending_classes.get_nowait()
                except Empty:
                    pass
                self._pending_classes.put_nowait(classes)
            self._pending_classes_snapshot = classes
        self.keyword_queue_changed.emit(classes)

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

                detections: list[Detection] = []
                if self._detector is not None:
                    with self._pending_classes_lock:
                        try:
                            classes = self._pending_classes.get_nowait()
                        except Empty:
                            classes = None
                        else:
                            self._pending_classes_snapshot = None
                    if classes is not None:
                        self.keyword_queue_changed.emit(())
                    if classes is not None:
                        self._detector.set_classes(classes)
                        self.active_classes_changed.emit(classes)
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
                image = frame_to_qimage(frame)
                self.frame_ready.emit(image)
                if detections:
                    self.detection_frame_ready.emit(image, detections)
        except (cv2.error, OSError, RuntimeError, TypeError, ValueError) as error:
            self.error.emit(f"Desktop preview failed: {error}")
        finally:
            if capture is not None:
                capture.release()
            if self._detector is not None:
                self._detector.close()
