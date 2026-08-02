"""Tests for the native Apple SoundAnalysis adapter."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest.mock import patch

from models.model_config import AppleSoundAnalysisConfig
from models.sound.apple_sound_analysis import (
    AppleSoundAnalysisClassifier,
    SoundAnalysis,
    _create_results_observer,
)


class FakeClassification:
    """Expose the subset of SNClassification used by the adapter."""

    def __init__(self, label: str, confidence: float) -> None:
        self._label = label
        self._confidence = confidence

    def identifier(self) -> str:
        return self._label

    def confidence(self) -> float:
        return self._confidence


class FakeResult:
    """Expose a timestamp and native-style classification list."""

    def __init__(self, classifications: list[FakeClassification]) -> None:
        self._classifications = classifications

    def timeRange(self) -> SimpleNamespace:
        return SimpleNamespace(start=2.0, duration=3.0)

    def classifications(self) -> list[FakeClassification]:
        return self._classifications


def make_config() -> AppleSoundAnalysisConfig:
    """Return deterministic policy shared by adapter tests."""
    return AppleSoundAnalysisConfig(
        backend="apple_soundanalysis",
        classifier_version=1,
        window_seconds=3.0,
        overlap=0.5,
        top_k=2,
        thresholds={"cat_meow": 0.5, "dog_bark": 0.6},
    )


@unittest.skipUnless(sys.platform == "darwin", "Apple framework requires macOS")
class AppleSoundAnalysisTests(unittest.TestCase):
    """Verify filtering, timestamps, native labels, and path validation."""

    def test_observer_keeps_configured_labels_above_their_thresholds(self) -> None:
        observer = _create_results_observer(make_config())
        result = FakeResult(
            [
                FakeClassification("cat_meow", 0.8),
                FakeClassification("dog_bark", 0.4),
                FakeClassification("speech", 0.99),
            ]
        )

        with patch(
            "models.sound.apple_sound_analysis.CoreMedia.CMTimeGetSeconds",
            side_effect=float,
        ):
            observer.request_didProduceResult_(None, result)

        self.assertEqual(len(observer.windows), 1)
        window = observer.windows[0]
        self.assertEqual(window.start_seconds, 2.0)
        self.assertEqual(window.end_seconds, 5.0)
        self.assertEqual(len(window.predictions), 1)
        self.assertEqual(window.predictions[0].label, "cat_meow")
        self.assertEqual(window.predictions[0].confidence, 0.8)

    def test_reports_a_missing_audio_file_before_native_analysis(self) -> None:
        classifier = AppleSoundAnalysisClassifier(make_config())
        missing_path = Path(tempfile.gettempdir()) / "missing-sound-file.wav"

        with self.assertRaisesRegex(FileNotFoundError, "Audio file was not found"):
            classifier.classify_file(missing_path)

    @unittest.skipIf(SoundAnalysis is None, "SoundAnalysis dependency is unavailable")
    def test_builtin_classifier_contains_required_project_labels(self) -> None:
        classifier = AppleSoundAnalysisClassifier(make_config())

        labels = set(classifier.known_labels)

        self.assertTrue(
            {
                "cat_meow",
                "dog_bark",
                "engine",
                "engine_accelerating_revving",
                "race_car",
            }.issubset(labels)
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
