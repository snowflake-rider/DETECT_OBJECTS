"""Load and validate configuration for local AI model artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
import tomllib

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODELS_CONFIG_PATH = PROJECT_ROOT / "config" / "models.toml"


@dataclass(frozen=True)
class YoloWorldConfig:
    """Validated YOLO-World runtime defaults."""

    weights: Path
    confidence: float
    image_size: tuple[int, int]


@dataclass(frozen=True)
class AppleSoundAnalysisConfig:
    """Validated settings for Apple's built-in sound classifier."""

    backend: str
    classifier_version: int
    window_seconds: float
    overlap: float
    top_k: int
    thresholds: Mapping[str, float]


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


def load_yolo_world_config(
    config_path: str | Path = DEFAULT_MODELS_CONFIG_PATH,
) -> YoloWorldConfig:
    """Load YOLO-World settings, resolving weights relative to the TOML file."""
    resolved_config_path, document = _load_document(config_path)

    try:
        section = document["vision"]["yolo_world"]
    except (KeyError, TypeError) as error:
        raise ValueError(
            "Model configuration requires a [vision.yolo_world] section"
        ) from error

    if not isinstance(section, dict):
        raise ValueError("[vision.yolo_world] must be a TOML table")

    weights_value = section.get("weights")
    if not isinstance(weights_value, str) or not weights_value.strip():
        raise ValueError("vision.yolo_world.weights must be a non-empty path")

    weights = Path(weights_value).expanduser()
    if not weights.is_absolute():
        weights = resolved_config_path.parent / weights
    weights = weights.resolve()

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


def load_apple_sound_analysis_config(
    config_path: str | Path = DEFAULT_MODELS_CONFIG_PATH,
) -> AppleSoundAnalysisConfig:
    """Load and validate the native macOS sound-classifier settings."""
    _, document = _load_document(config_path)

    try:
        section = document["audio"]["sound_classifier"]
    except (KeyError, TypeError) as error:
        raise ValueError(
            "Model configuration requires an [audio.sound_classifier] section"
        ) from error

    if not isinstance(section, dict):
        raise ValueError("[audio.sound_classifier] must be a TOML table")

    backend = section.get("backend")
    if backend != "apple_soundanalysis":
        raise ValueError("audio.sound_classifier.backend must be 'apple_soundanalysis'")

    classifier_version = section.get("classifier_version")
    if isinstance(classifier_version, bool) or classifier_version != 1:
        raise ValueError("audio.sound_classifier.classifier_version must be 1")

    window_seconds = _number_in_range(
        section.get("window_seconds"),
        name="audio.sound_classifier.window_seconds",
        minimum=0.5,
        maximum=15.0,
    )
    overlap = _number_in_range(
        section.get("overlap"),
        name="audio.sound_classifier.overlap",
        minimum=0.0,
        maximum=1.0,
        maximum_inclusive=False,
    )

    top_k = section.get("top_k")
    if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k <= 0:
        raise ValueError("audio.sound_classifier.top_k must be a positive integer")

    thresholds_value = section.get("thresholds")
    if not isinstance(thresholds_value, dict) or not thresholds_value:
        raise ValueError(
            "audio.sound_classifier.thresholds must contain at least one sound"
        )

    thresholds: dict[str, float] = {}
    for label, threshold in thresholds_value.items():
        if not isinstance(label, str) or not label.strip():
            raise ValueError("sound threshold labels must be non-empty strings")
        thresholds[label] = _number_in_range(
            threshold,
            name=f"audio.sound_classifier.thresholds.{label}",
            minimum=0.0,
            maximum=1.0,
        )

    return AppleSoundAnalysisConfig(
        backend=backend,
        classifier_version=classifier_version,
        window_seconds=window_seconds,
        overlap=overlap,
        top_k=top_k,
        thresholds=thresholds,
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
