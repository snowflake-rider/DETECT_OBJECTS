"""Download model artifacts required by the main ODIA application."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from detect_objects.models.model_config import (
    DEFAULT_MODELS_CONFIG_PATH,
    configured_yolo_world_weights_path,
)

# Callable describes something that can be called like a function.
# Its format is Callable[[argument types], return type]. The inner brackets
# list the arguments; the final type describes what the function returns.
# Callable[[Path], str | Path] means:
#   - it receives one Path argument;
#   - it returns either a string or a Path.
#
# More examples:
#   Callable[[], int]              takes no arguments and returns an int
#   Callable[[Path, str], bool]    takes Path and str and returns a bool
#   Callable[..., Path]            accepts any arguments and returns a Path
#
# Callable[Path] would be incomplete because it does not provide both parts.
#
# Example:
#   def save_model(destination: Path) -> Path:
#       destination.write_bytes(b"model data")
#       return destination
#
# save_model matches ModelDownloader and can be passed as downloader=save_model.
ModelDownloader = Callable[[Path], str | Path]


def _download_ultralytics_asset(destination: Path) -> str:
    """Download a recognized Ultralytics asset to an explicit destination."""
    # Import Ultralytics only when a real download is required.
    from ultralytics.utils.downloads import attempt_download_asset

    return attempt_download_asset(destination)


def download_required_models(
    config_path: str | Path = DEFAULT_MODELS_CONFIG_PATH,
    *,
    downloader: ModelDownloader | None = None,
) -> tuple[Path, ...]:
    """Ensure every model required at application startup is available locally."""
    # config_path uses the project's normal models.toml unless another path is
    # supplied. The * makes downloader a named-only argument: downloader=...
    # None means that normal setup should use the real downloader.

    # Read models.toml and turn its configured weights value into a full path.
    weights = configured_yolo_world_weights_path(config_path)

    # Create the destination directory and any missing parent directories.
    # exist_ok=True means it is not an error when the directory already exists.
    weights.parent.mkdir(parents=True, exist_ok=True)

    # Avoid downloading the model again when the weights file already exists.
    if weights.is_file():
        print(f"YOLO-World weights already available: {weights}")
    else:
        print(f"Downloading YOLO-World weights to: {weights}")

        # Tests can provide a small fake downloader. Normal setup passes None,
        # so "or" selects the real Ultralytics downloader instead.
        (downloader or _download_ultralytics_asset)(weights)

    # Path.is_file() is True only when the path exists and is a regular file.
    # not reverses that result, so this block runs when the weights file is
    # still missing after the downloader finishes.
    if not weights.is_file():
        raise RuntimeError(f"YOLO-World download did not produce: {weights}")

    # (weights,) is a tuple containing one Path. The comma creates the tuple;
    # (weights) alone would still be just a Path. Returning a tuple keeps the
    # result collection-shaped if more required model files are added later.
    return (weights,)


def main() -> int:
    """Provision required model files for shell bootstrap scripts."""
    download_required_models()
    print("Required model artifacts are ready.")

    # Returning 0 tells the shell that this script completed successfully.
    return 0


# This block runs only when Python executes this file directly. Importing the
# module from a test defines its functions without automatically downloading.
if __name__ == "__main__":
    raise SystemExit(main())
