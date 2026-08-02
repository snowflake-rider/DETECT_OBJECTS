"""Create and expose sound-classification backends."""

from __future__ import annotations

from pathlib import Path

from models.model_config import (
    DEFAULT_MODELS_CONFIG_PATH,
    load_apple_sound_analysis_config,
)
from models.sound.apple_sound_analysis import AppleSoundAnalysisClassifier
from models.sound.base import SoundClassifier, SoundPrediction, SoundWindow


def create_sound_classifier(
    config_path: str | Path = DEFAULT_MODELS_CONFIG_PATH,
) -> SoundClassifier:
    """Create the configured sound-classifier backend."""
    config = load_apple_sound_analysis_config(config_path)
    return AppleSoundAnalysisClassifier(config)


__all__ = [
    "AppleSoundAnalysisClassifier",
    "SoundClassifier",
    "SoundPrediction",
    "SoundWindow",
    "create_sound_classifier",
]
