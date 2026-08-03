"""Create and expose the prompt-guided audio separator."""

from __future__ import annotations

from pathlib import Path

from detect_objects.models.model_config import (
    DEFAULT_MODELS_CONFIG_PATH,
    load_sam_audio_mlx_config,
)
from .sam_audio_mlx import SamAudioMlxSeparator


def create_sound_separator(
    config_path: str | Path = DEFAULT_MODELS_CONFIG_PATH,
) -> SamAudioMlxSeparator:
    """Create the configured prompt-guided sound separator."""
    config = load_sam_audio_mlx_config(config_path)
    return SamAudioMlxSeparator(config)


__all__ = [
    "SamAudioMlxSeparator",
    "create_sound_separator",
]
