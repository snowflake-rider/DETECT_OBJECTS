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
    "sounddevice",
    "soundfile",
    "textual",
    "torch",
    "ultralytics",
    "whisper",
)


def required_modules() -> tuple[str, ...]:
    """Return base imports plus platform-specific Apple dependencies."""
    modules = list(REQUIRED_MODULES)
    if platform.system() == "Darwin":
        modules.extend(("AVFoundation", "SoundAnalysis"))
        if platform.machine() == "arm64":
            modules.append("mlx_audio")
    return tuple(modules)


def main() -> int:
    """Print verification failures and return a shell-friendly status code."""
    errors: list[str] = []

    if sys.version_info[:2] != (3, 11):
        errors.append(f"Python 3.11 is required; found {sys.version.split()[0]}.")

    missing_modules = [
        module
        for module in required_modules()
        if importlib.util.find_spec(module) is None
    ]
    if missing_modules:
        errors.append(f"Missing Python modules: {', '.join(missing_modules)}")

    project_root = Path(__file__).resolve().parent.parent
    required_files = (
        project_root / "config" / "models.toml",
        project_root / "samples" / "audio" / "cat_meow.wav",
    )
    missing_files = [str(path) for path in required_files if not path.is_file()]
    if missing_files:
        errors.append(f"Missing repository files: {', '.join(missing_files)}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(f"Python: {sys.version.split()[0]}")
    print(f"Platform: {platform.system()} {platform.machine()}")
    print(f"Project package: {importlib.util.find_spec('detect_objects').origin}")
    print("Environment verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
