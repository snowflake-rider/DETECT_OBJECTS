"""Load and validate configuration for local AI model artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
import tomllib

from ..paths import PROJECT_ROOT

DEFAULT_MODELS_CONFIG_PATH = PROJECT_ROOT / "config" / "models.toml"


@dataclass(frozen=True)
class YoloWorldConfig:
    """Validated YOLO-World runtime defaults."""

    weights: Path
    confidence: float
    image_size: tuple[int, int]


@dataclass(frozen=True)
class SamAudioMlxConfig:
    """Validated settings for prompt-guided SAM-Audio separation."""

    backend: str
    model_id: str
    artifact_dir: Path
    text_encoder_id: str
    text_encoder_dir: Path
    chunk_seconds: float
    overlap_seconds: float
    ode_step_size: float
    ode_decode_chunk_size: int
    seed: int


def _load_document(config_path: str | Path) -> tuple[Path, dict[str, Any]]:
    """Read a TOML configuration file and return its resolved path and data."""
    resolved_config_path = Path(config_path).expanduser().resolve()

    try:
        with resolved_config_path.open("rb") as config_file:
            document = tomllib.load(config_file)
    except FileNotFoundError as error:
        raise FileNotFoundError(
            f"Model configuration was not found: {resolved_config_path}"
        ) from error
    except tomllib.TOMLDecodeError as error:
        raise ValueError(
            f"Model configuration is invalid TOML: {resolved_config_path}"
        ) from error

    return resolved_config_path, document


def _load_yolo_world_section(
    config_path: str | Path = DEFAULT_MODELS_CONFIG_PATH,
) -> tuple[Path, dict[str, Any]]:
    """Load and validate the YOLO-World TOML section."""
    resolved_config_path, document = _load_document(config_path)

    try:
        section = document["vision"]["yolo_world"]
    except (KeyError, TypeError) as error:
        raise ValueError(
            "Model configuration requires a [vision.yolo_world] section"
        ) from error

    if not isinstance(section, dict):
        raise ValueError("[vision.yolo_world] must be a TOML table")

    return resolved_config_path, section


def _resolve_yolo_world_weights(
    resolved_config_path: Path,
    section: Mapping[str, Any],
) -> Path:
    """Resolve the configured YOLO-World weights path without requiring it."""
    weights_value = section.get("weights")
    if not isinstance(weights_value, str) or not weights_value.strip():
        raise ValueError("vision.yolo_world.weights must be a non-empty path")

    weights = Path(weights_value).expanduser()
    if not weights.is_absolute():
        weights = resolved_config_path.parent / weights
    weights = weights.resolve()

    return weights


def configured_yolo_world_weights_path(
    config_path: str | Path = DEFAULT_MODELS_CONFIG_PATH,
) -> Path:
    """Return the configured YOLO-World weights path, even when it is missing."""
    resolved_config_path, section = _load_yolo_world_section(config_path)
    return _resolve_yolo_world_weights(resolved_config_path, section)


def load_yolo_world_config(
    config_path: str | Path = DEFAULT_MODELS_CONFIG_PATH,
) -> YoloWorldConfig:
    """Load YOLO-World settings, resolving weights relative to the TOML file."""
    resolved_config_path, section = _load_yolo_world_section(config_path)
    weights = _resolve_yolo_world_weights(resolved_config_path, section)

    if not weights.is_file():
        raise FileNotFoundError(f"YOLO-World weights were not found: {weights}")

    confidence_value = section.get("confidence")
    if (
        isinstance(confidence_value, bool)
        or not isinstance(confidence_value, (int, float))
        or not 0.0 <= float(confidence_value) <= 1.0
    ):
        raise ValueError(
            "vision.yolo_world.confidence must be a number from 0.0 to 1.0"
        )

    image_size_value = section.get("image_size")
    if (
        not isinstance(image_size_value, list)
        or len(image_size_value) != 2
        or any(
            isinstance(dimension, bool)
            or not isinstance(dimension, int)
            or dimension <= 0
            for dimension in image_size_value
        )
    ):
        raise ValueError(
            "vision.yolo_world.image_size must contain two positive integers"
        )

    return YoloWorldConfig(
        weights=weights,
        confidence=float(confidence_value),
        image_size=(image_size_value[0], image_size_value[1]),
    )


def load_sam_audio_mlx_config(
    config_path: str | Path = DEFAULT_MODELS_CONFIG_PATH,
) -> SamAudioMlxConfig:
    """Load and validate the Apple-Silicon SAM-Audio separator settings."""
    resolved_config_path, document = _load_document(config_path)

    try:
        section = document["audio"]["source_separator"]
    except (KeyError, TypeError) as error:
        raise ValueError(
            "Model configuration requires an [audio.source_separator] section"
        ) from error

    if not isinstance(section, dict):
        raise ValueError("[audio.source_separator] must be a TOML table")

    backend = section.get("backend")
    if backend != "sam_audio_mlx":
        raise ValueError("audio.source_separator.backend must be 'sam_audio_mlx'")

    model_id = section.get("model_id")
    if not isinstance(model_id, str) or not model_id.strip():
        raise ValueError("audio.source_separator.model_id must be non-empty")

    artifact_dir_value = section.get("artifact_dir")
    if not isinstance(artifact_dir_value, str) or not artifact_dir_value.strip():
        raise ValueError("audio.source_separator.artifact_dir must be a path")
    artifact_dir = Path(artifact_dir_value).expanduser()
    if not artifact_dir.is_absolute():
        artifact_dir = resolved_config_path.parent / artifact_dir
    artifact_dir = artifact_dir.resolve()

    text_encoder_id = section.get("text_encoder_id")
    if not isinstance(text_encoder_id, str) or not text_encoder_id.strip():
        raise ValueError("audio.source_separator.text_encoder_id must be non-empty")

    text_encoder_dir_value = section.get("text_encoder_dir")
    if (
        not isinstance(text_encoder_dir_value, str)
        or not text_encoder_dir_value.strip()
    ):
        raise ValueError("audio.source_separator.text_encoder_dir must be a path")
    text_encoder_dir = Path(text_encoder_dir_value).expanduser()
    if not text_encoder_dir.is_absolute():
        text_encoder_dir = resolved_config_path.parent / text_encoder_dir
    text_encoder_dir = text_encoder_dir.resolve()

    chunk_seconds = _positive_number(
        section.get("chunk_seconds"),
        name="audio.source_separator.chunk_seconds",
    )
    overlap_seconds = _number_in_range(
        section.get("overlap_seconds"),
        name="audio.source_separator.overlap_seconds",
        minimum=0.0,
        maximum=chunk_seconds,
        maximum_inclusive=False,
    )
    ode_step_size = _number_in_range(
        section.get("ode_step_size"),
        name="audio.source_separator.ode_step_size",
        minimum=0.0,
        maximum=1.0,
        maximum_inclusive=False,
    )
    if ode_step_size == 0.0:
        raise ValueError("audio.source_separator.ode_step_size must be greater than 0")

    ode_decode_chunk_size = section.get("ode_decode_chunk_size")
    if (
        isinstance(ode_decode_chunk_size, bool)
        or not isinstance(ode_decode_chunk_size, int)
        or ode_decode_chunk_size <= 0
    ):
        raise ValueError(
            "audio.source_separator.ode_decode_chunk_size must be a positive integer"
        )

    seed = section.get("seed")
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ValueError("audio.source_separator.seed must be a non-negative integer")

    return SamAudioMlxConfig(
        backend=backend,
        model_id=model_id.strip(),
        artifact_dir=artifact_dir,
        text_encoder_id=text_encoder_id.strip(),
        text_encoder_dir=text_encoder_dir,
        chunk_seconds=chunk_seconds,
        overlap_seconds=overlap_seconds,
        ode_step_size=ode_step_size,
        ode_decode_chunk_size=ode_decode_chunk_size,
        seed=seed,
    )


def _number_in_range(
    value: object,
    *,
    name: str,
    minimum: float,
    maximum: float,
    maximum_inclusive: bool = True,
) -> float:
    """Validate and normalize a numeric configuration value."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")

    number = float(value)
    maximum_valid = number <= maximum if maximum_inclusive else number < maximum
    if number < minimum or not maximum_valid:
        upper = "]" if maximum_inclusive else ")"
        raise ValueError(f"{name} must be in [{minimum}, {maximum}{upper}")

    return number


def _positive_number(value: object, *, name: str) -> float:
    """Validate and normalize a number that must be greater than zero."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    number = float(value)
    if number <= 0.0:
        raise ValueError(f"{name} must be greater than 0")
    return number
