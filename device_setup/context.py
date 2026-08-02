"""Values selected and shared during one application run."""

# Delay reading type hints, so Camera and Audio do not need runtime imports here.
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .environment import Environment

# TYPE_CHECKING is False while Python runs, so these imports are skipped.
# Editors such as Pylance treat it as True and learn what Camera and Audio mean.
# This avoids loading camera.py and audio.py just to define Context.
if TYPE_CHECKING:
    from .audio import Audio
    from .camera import Camera


@dataclass(frozen=True)
class Context:
    """Keep the detected environment and selected input devices for this run."""

    environment: Environment
    camera: Camera
    audio: Audio
