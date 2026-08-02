"""Construct runtime model managers from user-selected preset identifiers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .catalog import get_model_option

if TYPE_CHECKING:
    from ..voice_text_convert.mic_whisper_manager import Whisper_Audio_Manager
    from .yolo_world_module import YOLO_World_Manager


def create_vision_manager(model_id: str) -> YOLO_World_Manager:
    """Construct the vision manager selected by the setup context."""
    from .yolo_world_module import YOLO_World_Manager

    option = get_model_option(model_id, kind="vision")

    if option.id == "yolo_world_v2_small":
        return YOLO_World_Manager()

    raise ValueError(f"Unsupported vision model preset: {model_id}")


def create_voice_manager(
    model_id: str,
    *,
    device_id: int,
) -> Whisper_Audio_Manager:
    """Construct the voice manager selected by the setup context."""
    from ..voice_text_convert.mic_whisper_manager import Whisper_Audio_Manager

    option = get_model_option(model_id, kind="voice")
    whisper_variants = {
        "whisper_base_ko": "base",
        "whisper_tiny_ko": "tiny",
    }

    try:
        whisper_model_name = whisper_variants[option.id]
    except KeyError as error:
        raise ValueError(f"Unsupported voice model preset: {model_id}") from error

    return Whisper_Audio_Manager(
        device_id=device_id,
        model_name=whisper_model_name,
        sample_rate=16000,
        channels=1,
        block_size=1024,
        record_seconds=5,
        language="ko",
    )
