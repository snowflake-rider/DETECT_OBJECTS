"""Model presets exposed to setup screens and runtime factories."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ModelKind = Literal["vision", "voice"]

DEFAULT_VISION_MODEL_ID = "yolo_world_v2_small"
DEFAULT_VOICE_MODEL_ID = "whisper_base_ko"


@dataclass(frozen=True)
class ModelOption:
    """User-facing information for one selectable model preset."""

    id: str
    kind: ModelKind
    name: str
    description: str
    recommended: bool = False

    @property
    def display_name(self) -> str:
        """Return the label shown in a model selection control."""
        suffix = " (Recommended)" if self.recommended else ""
        return f"{self.name}{suffix}"


@dataclass(frozen=True)
class ModelSelection:
    """Stable preset identifiers selected for one application run."""

    vision_id: str = DEFAULT_VISION_MODEL_ID
    voice_id: str = DEFAULT_VOICE_MODEL_ID

    def __post_init__(self) -> None:
        get_model_option(self.vision_id, kind="vision")
        get_model_option(self.voice_id, kind="voice")


MODEL_OPTIONS: tuple[ModelOption, ...] = (
    ModelOption(
        id=DEFAULT_VISION_MODEL_ID,
        kind="vision",
        name="YOLO-World v2 Small",
        description="Fast open-vocabulary object detection with live class switching.",
        recommended=True,
    ),
    ModelOption(
        id=DEFAULT_VOICE_MODEL_ID,
        kind="voice",
        name="Whisper Base — Korean",
        description="Balanced Korean transcription speed and accuracy.",
        recommended=True,
    ),
    ModelOption(
        id="whisper_tiny_ko",
        kind="voice",
        name="Whisper Tiny — Korean",
        description="Faster Korean transcription with lower recognition accuracy.",
    ),
)


def list_model_options(kind: ModelKind) -> tuple[ModelOption, ...]:
    """Return the selectable presets for one model kind."""
    return tuple(option for option in MODEL_OPTIONS if option.kind == kind)


def get_model_option(model_id: str, *, kind: ModelKind | None = None) -> ModelOption:
    """Return and validate one model preset by its stable identifier."""
    for option in MODEL_OPTIONS:
        if option.id == model_id and (kind is None or option.kind == kind):
            return option

    expected = f" {kind}" if kind is not None else ""
    raise ValueError(f"Unknown{expected} model preset: {model_id}")
