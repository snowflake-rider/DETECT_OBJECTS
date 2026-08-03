"""Persist spoken search instructions and matching detection snapshots."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
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
    """One requested object visible in a saved snapshot."""

    class_name: str
    confidence: float


@dataclass(frozen=True)
class SnapshotEvent:
    """One saved image and the requested objects visible inside it."""

    timestamp: str
    snapshot: str
    objects: tuple[FoundObject, ...]


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
        self._detections: list[SnapshotEvent] = []
        self._last_snapshot_at: datetime | None = None

        self.session_dir = root / self._session_id
        self._snapshots_dir = self.session_dir / "snapshots"
        self.events_path = self.session_dir / "events.json"
        self._snapshots_dir.mkdir(parents=True, exist_ok=True)
        self._write_events()

    @property
    def snapshot_paths(self) -> tuple[Path, ...]:
        """Return saved snapshots in capture order."""
        return tuple(self.session_dir / event.snapshot for event in self._detections)

    @property
    def has_snapshots(self) -> bool:
        """Return whether this session contains a matching detection image."""
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
    ) -> SnapshotEvent | None:
        """Save a frame when it contains a requested class outside the cooldown."""
        matching = [
            detection
            for detection in detections
            if detection.class_name in self._active_classes
        ]
        if not matching:
            return None

        captured_at = self._now()
        if self._last_snapshot_at is not None:
            elapsed = (captured_at - self._last_snapshot_at).total_seconds()
            if elapsed < self._cooldown_seconds:
                return None

        class_slug = "-".join(
            _slugify(detection.class_name) for detection in matching[:3]
        )
        relative_path = Path("snapshots") / (
            f"{captured_at:%Y%m%dT%H%M%S%f}-{class_slug}.png"
        )
        snapshot_path = self.session_dir / relative_path
        if not image.save(str(snapshot_path), "PNG"):
            raise OSError(f"Could not save story snapshot: {snapshot_path}")

        event = SnapshotEvent(
            timestamp=captured_at.isoformat(),
            snapshot=relative_path.as_posix(),
            objects=tuple(
                FoundObject(
                    class_name=detection.class_name,
                    confidence=round(detection.confidence, 4),
                )
                for detection in matching
            ),
        )
        self._detections.append(event)
        self._last_snapshot_at = captured_at
        self._write_events()
        return event

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
