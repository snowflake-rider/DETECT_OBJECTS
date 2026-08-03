"""Verify that ODIA's Python environment and repository resources are ready."""

from __future__ import annotations

import importlib.util
import platform
import sys
from pathlib import Path

REQUIRED_MODULES = (
    "detect_objects",
    "cv2",
    "cv2_enumerate_cameras",
    "numpy",
    "PySide6",
    "sounddevice",
    "soundfile",
    "textual",
    "torch",
    "ultralytics",
    "whisper",
)


def main() -> int:
    """Print verification failures and return a shell-friendly status code."""
    # Store every problem so the user can fix them together instead of running
    # setup again after discovering each problem separately.
    errors: list[str] = []

    # sys.version_info contains the running Python version as numbers such as
    # major=3, minor=11, and micro=15. [:2] selects only major and minor.
    if sys.version_info[:2] != (3, 11):
        errors.append(f"Python 3.11 is required; found {sys.version.split()[0]}.")

    # importlib.util.find_spec(name) asks Python's import system whether it can
    # locate a module. It returns module information when found or None when
    # missing, without importing and running the target module itself.
    missing_modules = [
        module
        for module in REQUIRED_MODULES
        if importlib.util.find_spec(module) is None
    ]
    if missing_modules:
        errors.append(f"Missing Python modules: {', '.join(missing_modules)}")

    # __file__ is the path Python used to load this verify_environment.py file.
    # Path(__file__) converts that string into a Path object.
    # resolve() makes it an absolute path, removes parts such as "..", and
    # resolves symbolic links when possible.
    #
    # Example resolved path:
    #   /project/detect_objects/bootstrap/tools/verify_environment.py
    #
    # parents contains every directory above the file:
    #   parents[0] = /project/detect_objects/bootstrap/tools
    #   parents[1] = /project/detect_objects/bootstrap
    #   parents[2] = /project/detect_objects        <- project root
    #
    # Therefore, this starts with the current file and walks up three directory
    # levels to find the project root, regardless of the current shell directory.
    project_root = Path(__file__).resolve().parents[2]

    # These repository files are required by setup and the device tests.
    # For Path objects, / joins path components; it does not perform division.
    # This expression:
    #   project_root / "config" / "models.toml"
    # constructs:
    #   /project/detect_objects/config/models.toml
    # Path chooses the correct path separator for the operating system.
    required_files = [
        project_root / "config" / "models.toml",
        project_root / "samples" / "audio" / "cat_meow.wav",
    ]

    # The model configuration determines where the YOLO weights should exist.
    # If configuration cannot be imported or read, record the error and keep
    # checking the other files.
    try:
        from detect_objects.models.model_config import (
            configured_yolo_world_weights_path,
        )

        required_files.append(configured_yolo_world_weights_path())
    except (ImportError, OSError, TypeError, ValueError) as error:
        errors.append(f"Unable to resolve configured model artifacts: {error}")

    # Build a list containing every required path that is not a regular file.
    missing_files = [str(path) for path in required_files if not path.is_file()]
    if missing_files:
        errors.append(f"Missing required files: {', '.join(missing_files)}")

    # Return 1 when any check failed. Shell scripts treat nonzero as failure.
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    # All checks passed, so print useful environment details and return 0.
    print(f"Python: {sys.version.split()[0]}")
    print(f"Platform: {platform.system()} {platform.machine()}")
    print(f"Project package: {importlib.util.find_spec('detect_objects').origin}")
    print("Environment verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
