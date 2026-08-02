"""Command-line smoke test for the configured sound classifier."""

from __future__ import annotations

import argparse
from pathlib import Path

from models.sound import create_sound_classifier


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Classify an audio file with Apple SoundAnalysis.",
    )
    parser.add_argument("audio_file", type=Path, help="Path to an audio file")
    return parser.parse_args()


def main() -> None:
    """Print configured sound detections grouped by analysis window."""
    args = _parse_args()
    classifier = create_sound_classifier()
    for window in classifier.classify_file(args.audio_file):
        for prediction in window.predictions:
            print(
                f"{window.start_seconds:.2f}-{window.end_seconds:.2f}s "
                f"{prediction.label}: {prediction.confidence:.3f}"
            )


if __name__ == "__main__":
    main()
