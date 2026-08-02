"""Values selected and shared during one application run."""

# Delay reading type hints, so device modules are not loaded at runtime here.
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ..models.catalog import ModelSelection
from .environment import Environment

# TYPE_CHECKING is False while Python runs, so these imports are skipped.
# Editors such as Pylance treat it as True and learn the selected device types.
# This avoids loading camera.py and audio.py just to define Context.
if TYPE_CHECKING:
    from .audio import AudioInput, AudioOutput
    from .camera import Camera


@dataclass(frozen=True)
class Context:
    """Keep the environment and selected devices for this application run."""

    environment: Environment
    camera: Camera
    audio_input: AudioInput
    audio_output: AudioOutput
    models: ModelSelection = field(default_factory=ModelSelection)
