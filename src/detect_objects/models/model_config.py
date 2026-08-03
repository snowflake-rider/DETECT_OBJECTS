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
