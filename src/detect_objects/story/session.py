"""Persist spoken search instructions and matching YOLO object crops."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import TYPE_CHECKING
from uuid import uuid4

from PySide6.QtGui import QImage

if TYPE_CHECKING:
    from ..desktop.yolo_detection import Detection

Clock = Callable[[], datetime]


@dataclass(frozen=True)
class FoundObject:
    """One requested object represented by a saved crop."""

    class_name: str
    confidence: float


@dataclass(frozen=True)
class CropEvent:
    """One saved YOLO object crop available to the Story queue."""

    timestamp: str
    crop: str
    objects: tuple[FoundObject, ...]
    selected: bool = True


class SessionRecorder:
    """Collect matching detections inside one presentation story session."""

    def __init__(
        self,
        root: Path,
        *,
        session_id: str | None = None,
        cooldown_seconds: float = 3.0,
        now: Clock | None = None,
    ) -> None:
        if cooldown_seconds < 0:
            raise ValueError("cooldown_seconds must not be negative")

        self._now = now or (lambda: datetime.now(timezone.utc))
        started_at = self._now()
        self._session_id = session_id or (
            f"{started_at:%Y%m%dT%H%M%S}-{uuid4().hex[:8]}"
        )
        self._cooldown_seconds = cooldown_seconds
        self._started_at = started_at.isoformat()
        self._active_classes: tuple[str, ...] = ()
        self._instructions: list[dict[str, object]] = []
        self._detections: list[CropEvent] = []
        self._last_crop_at: datetime | None = None

        self.session_dir = root / self._session_id
        self._crops_dir = self.session_dir / "crops"
        self.events_path = self.session_dir / "events.json"
        self._crops_dir.mkdir(parents=True, exist_ok=True)
        self._write_events()

    @property
    def crop_paths(self) -> tuple[Path, ...]:
        """Return saved YOLO crops in capture order."""
        return tuple(self.session_dir / event.crop for event in self._detections)

    @property
    def selected_crop_paths(self) -> tuple[Path, ...]:
        """Return only crops currently queued for Codex."""
        return tuple(
            self.session_dir / event.crop
            for event in self._detections
            if event.selected
        )

    @property
    def has_crops(self) -> bool:
        """Return whether this session contains any saved object crop."""
        return bool(self._detections)

    def record_instruction(self, text: str, classes: Sequence[str]) -> None:
        """Set requested classes and append the spoken or typed instruction."""
        normalized_classes = tuple(
            dict.fromkeys(name.strip() for name in classes if name.strip())
        )
        if not text.strip() or not normalized_classes:
            return

        self._active_classes = normalized_classes
        self._instructions.append(
            {
                "timestamp": self._now().isoformat(),
                "text": text.strip(),
                "classes": list(normalized_classes),
            }
        )
        self._write_events()

    def record_detection(
        self,
        image: QImage,
        detections: Sequence[Detection],
    ) -> tuple[CropEvent, ...]:
        """Save one box crop per requested detection outside the cooldown."""
        matching = [
            detection
            for detection in detections
            if detection.class_name in self._active_classes
        ]
        if not matching:
            return ()

        captured_at = self._now()
        if self._last_crop_at is not None:
            elapsed = (captured_at - self._last_crop_at).total_seconds()
            if elapsed < self._cooldown_seconds:
                return ()

        events: list[CropEvent] = []
        for position, detection in enumerate(matching, start=1):
            class_slug = _slugify(detection.class_name)
            relative_path = Path("crops") / (
                f"{captured_at:%Y%m%dT%H%M%S%f}-{class_slug}-{position:02d}.png"
            )
            crop_path = self.session_dir / relative_path
            crop = _crop_to_bounds(image, detection.bounds)
            if not crop.save(str(crop_path), "PNG"):
                raise OSError(f"Could not save story object crop: {crop_path}")

            events.append(
                CropEvent(
                    timestamp=captured_at.isoformat(),
                    crop=relative_path.as_posix(),
                    objects=(
                        FoundObject(
                            class_name=detection.class_name,
                            confidence=round(detection.confidence, 4),
                        ),
                    ),
                )
            )

        self._detections.extend(events)
        self._last_crop_at = captured_at
        self._write_events()
        return tuple(events)

    def set_crop_selected(self, crop_path: Path, selected: bool) -> None:
        """Include or exclude one displayed crop from the Codex queue."""
        relative_path = self._relative_crop_path(crop_path)
        for index, event in enumerate(self._detections):
            if event.crop == relative_path:
                self._detections[index] = replace(event, selected=selected)
                self._write_events()
                return
        raise ValueError(f"Crop does not belong to this session: {crop_path}")

    def remove_crop(self, crop_path: Path) -> None:
        """Remove one crop from disk and from the persisted event queue."""
        relative_path = self._relative_crop_path(crop_path)
        for index, event in enumerate(self._detections):
            if event.crop != relative_path:
                continue
            absolute_path = self.session_dir / event.crop
            absolute_path.unlink(missing_ok=True)
            del self._detections[index]
            self._write_events()
            return
        raise ValueError(f"Crop does not belong to this session: {crop_path}")

    def _relative_crop_path(self, crop_path: Path) -> str:
        candidate = crop_path.expanduser()
        if not candidate.is_absolute():
            candidate = self.session_dir / candidate
        try:
            relative = candidate.resolve().relative_to(self.session_dir.resolve())
        except ValueError as error:
            raise ValueError(
                f"Crop does not belong to this session: {crop_path}"
            ) from error
        return relative.as_posix()

    def _write_events(self) -> None:
        document = {
            "session_id": self._session_id,
            "started_at": self._started_at,
            "instructions": self._instructions,
            "detections": [asdict(event) for event in self._detections],
        }
        self.events_path.write_text(
            json.dumps(document, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "object"


def _crop_to_bounds(
    image: QImage,
    bounds: tuple[int, int, int, int],
) -> QImage:
    """Clamp one YOLO xyxy box and copy only that object region."""
    x1, y1, x2, y2 = bounds
    left = max(0, min(image.width(), x1))
    top = max(0, min(image.height(), y1))
    right = max(0, min(image.width(), x2))
    bottom = max(0, min(image.height(), y2))
    if right <= left or bottom <= top:
        raise ValueError(f"Detection bounds do not contain an image: {bounds}")
    return image.copy(left, top, right - left, bottom - top)
