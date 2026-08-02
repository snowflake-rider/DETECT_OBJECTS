"""Create and expose sound-classification backends."""

from __future__ import annotations

from pathlib import Path

from ..model_config import (
    DEFAULT_MODELS_CONFIG_PATH,
    load_apple_sound_analysis_config,
    load_sam_audio_mlx_config,
)
from .apple_sound_analysis import AppleSoundAnalysisClassifier
from .base import SoundClassifier, SoundPrediction, SoundWindow
from .sam_audio_mlx import SamAudioMlxSeparator


def create_sound_classifier(
    config_path: str | Path = DEFAULT_MODELS_CONFIG_PATH,
) -> SoundClassifier:
    """Create the configured sound-classifier backend."""
    config = load_apple_sound_analysis_config(config_path)
    return AppleSoundAnalysisClassifier(config)


def create_sound_separator(
    config_path: str | Path = DEFAULT_MODELS_CONFIG_PATH,
) -> SamAudioMlxSeparator:
    """Create the configured prompt-guided sound separator."""
    config = load_sam_audio_mlx_config(config_path)
    return SamAudioMlxSeparator(config)


__all__ = [
    "AppleSoundAnalysisClassifier",
    "SoundClassifier",
    "SoundPrediction",
    "SoundWindow",
    "create_sound_classifier",
    "create_sound_separator",
]
