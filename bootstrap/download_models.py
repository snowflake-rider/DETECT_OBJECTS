"""Download model artifacts required by the main ODIA application."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from detect_objects.models.model_config import (
    DEFAULT_MODELS_CONFIG_PATH,
    configured_yolo_world_weights_path,
)

ModelDownloader = Callable[[Path], str | Path]


def _download_ultralytics_asset(destination: Path) -> str:
    """Download a recognized Ultralytics asset to an explicit destination."""
    from ultralytics.utils.downloads import attempt_download_asset

    return attempt_download_asset(destination)


def download_required_models(
    config_path: str | Path = DEFAULT_MODELS_CONFIG_PATH,
    *,
    downloader: ModelDownloader | None = None,
) -> tuple[Path, ...]:
    """Ensure every model required at application startup is available locally."""
    weights = configured_yolo_world_weights_path(config_path)
    weights.parent.mkdir(parents=True, exist_ok=True)

    if weights.is_file():
        print(f"YOLO-World weights already available: {weights}")
    else:
        print(f"Downloading YOLO-World weights to: {weights}")
        (downloader or _download_ultralytics_asset)(weights)

    if not weights.is_file():
        raise RuntimeError(f"YOLO-World download did not produce: {weights}")

    return (weights,)


def main() -> int:
    """Provision required model files for shell bootstrap scripts."""
    download_required_models()
    print("Required model artifacts are ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
