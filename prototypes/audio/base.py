"""Shared sound-classification values and backend interface."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class SoundPrediction:
    """One sound label and its independent confidence score."""

    label: str
    confidence: float


@dataclass(frozen=True)
class SoundWindow:
    """Sound predictions associated with one audio time range."""

    start_seconds: float
    duration_seconds: float
    predictions: tuple[SoundPrediction, ...]

    @property
    def end_seconds(self) -> float:
        """Return the end of the analyzed window in seconds."""
        return self.start_seconds + self.duration_seconds


class SoundClassifier(Protocol):
    """Backend-neutral interface for sound classifiers."""

    def classify_file(self, audio_path: str | Path) -> list[SoundWindow]:
        """Classify an audio file into timestamped result windows."""
        ...
