"""Run and present YOLO detections for the PySide camera stream."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

import cv2
import numpy as np

from ..models.factory import create_vision_manager

if TYPE_CHECKING:
    from ultralytics.engine.results import Boxes

DETECTION_COLOR = (58, 163, 242)
DEFAULT_DETECTION_CLASSES = (
    "cell phone",
    "clock",
    "keyboard",
    "person",
)


@dataclass(frozen=True)
class Detection:
    """One model result expressed in source-frame pixel coordinates."""

    bounds: tuple[int, int, int, int]
    class_name: str
    confidence: float


class VisionManager(Protocol):
    """Model operations needed by the desktop detector."""

    @property
    def device_name(self) -> str: ...

    def load(self) -> None: ...

    def cache_class_embeddings(self, classes: Sequence[str]) -> None: ...

    def activate_cached_classes(self, classes: Sequence[str]) -> None: ...

    def predict(self, frame: np.ndarray) -> tuple[Boxes, dict[int, str]]: ...

    def close(self) -> None: ...


ManagerFactory = Callable[[str], VisionManager]


class YoloDetector:
    """Own the selected YOLO model and annotate desktop camera frames."""

    def __init__(
        self,
        model_id: str,
        *,
        manager_factory: ManagerFactory = create_vision_manager,
    ) -> None:
        self._model_id = model_id
        self._manager_factory = manager_factory
        self._manager: VisionManager | None = None

    @property
    def device_name(self) -> str:
        """Return the accelerator selected by the loaded model."""
        return self._require_manager().device_name

    def load(self) -> None:
        """Load the model and prepare the default detection classes."""
        if self._manager is not None:
            return

        manager = self._manager_factory(self._model_id)
        manager.load()
        manager.cache_class_embeddings(DEFAULT_DETECTION_CLASSES)
        manager.activate_cached_classes(DEFAULT_DETECTION_CLASSES)
        self._manager = manager

    def process(self, frame: np.ndarray) -> tuple[np.ndarray, list[Detection]]:
        """Predict and draw detections on one BGR camera frame."""
        boxes, names = self._require_manager().predict(frame)
        detections = detections_from_boxes(boxes, names)
        return draw_detections(frame, detections), detections

    def close(self) -> None:
        """Release the model and accelerator resources."""
        if self._manager is None:
            return
        self._manager.close()
        self._manager = None

    def _require_manager(self) -> VisionManager:
        if self._manager is None:
            raise RuntimeError("YOLO must be loaded before detection starts.")
        return self._manager


def format_detection_label(class_name: str, confidence: float) -> str:
    """Return a compact class label with rounded percentage confidence."""
    return f"{class_name.upper()} {confidence:.0%}"


def detections_from_boxes(
    boxes: Boxes,
    names: dict[int, str],
) -> list[Detection]:
    """Convert Ultralytics boxes into UI-friendly detection values."""
    detections = []

    for box in boxes:
        x1, y1, x2, y2 = box.xyxy[0].tolist()
        class_id = int(box.cls[0].item())
        detections.append(
            Detection(
                bounds=(int(x1), int(y1), int(x2), int(y2)),
                class_name=names[class_id],
                confidence=float(box.conf[0].item()),
            )
        )

    return detections


def draw_detections(
    frame: np.ndarray,
    detections: Sequence[Detection],
) -> np.ndarray:
    """Return a copy of the BGR frame with boxes and percentage labels."""
    annotated = frame.copy()

    for detection in detections:
        x1, y1, x2, y2 = detection.bounds
        cv2.rectangle(annotated, (x1, y1), (x2, y2), DETECTION_COLOR, 2)

        label = format_detection_label(
            detection.class_name,
            detection.confidence,
        )
        (text_width, text_height), baseline = cv2.getTextSize(
            label,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            1,
        )
        tag_bottom = max(y1, text_height + baseline + 8)
        tag_top = tag_bottom - text_height - baseline - 8
        cv2.rectangle(
            annotated,
            (x1, tag_top),
            (x1 + text_width + 12, tag_bottom),
            DETECTION_COLOR,
            -1,
        )
        cv2.putText(
            annotated,
            label,
            (x1 + 6, tag_bottom - baseline - 4),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (15, 18, 22),
            1,
            cv2.LINE_AA,
        )

    return annotated
