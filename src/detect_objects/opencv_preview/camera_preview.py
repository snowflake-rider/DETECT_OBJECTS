"""Display a selected camera in a dedicated OpenCV child process."""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from typing import Sequence

import cv2

from ..device_setup import Camera

RETURN_TO_TUI_HINT = "Press Q or Escape to return to TUI"


class CameraPreviewMode(str, Enum):
    """Supported OpenCV camera preview behaviors."""

    SNAPSHOT = "snapshot"
    STREAM = "stream"


@dataclass(frozen=True)
class CameraPreviewResult:
    """Outcome returned after an OpenCV preview window closes."""

    successful: bool
    error: str | None = None


def _read_frame(capture, attempts: int = 5):
    """Return the first readable frame from a warming camera."""
    for _ in range(attempts):
        success, frame = capture.read()
        if success and frame is not None:
            return frame
    return None


def _window_should_close(window_name: str, delay_ms: int) -> bool:
    """Return whether the user closed the window or pressed Q/Escape."""
    key = cv2.waitKey(delay_ms) & 0xFF
    if key in (ord("q"), 27):
        return True

    try:
        return cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1
    except cv2.error:
        return True


def show_camera_preview(
    *,
    index: int,
    backend: int,
    name: str,
    mode: CameraPreviewMode,
) -> CameraPreviewResult:
    """Own an OpenCV window until the user closes it."""
    capture = cv2.VideoCapture(index, backend)
    window_name = f"{name} — {mode.value.title()} Preview — {RETURN_TO_TUI_HINT}"

    try:
        if not capture.isOpened():
            return CameraPreviewResult(
                successful=False,
                error=f"Could not open '{name}'.",
            )

        frame = _read_frame(capture)
        if frame is None:
            return CameraPreviewResult(
                successful=False,
                error="Camera opened, but no frame was received.",
            )

        if mode is CameraPreviewMode.SNAPSHOT:
            cv2.imshow(window_name, frame)
            while not _window_should_close(window_name, 30):
                pass
            return CameraPreviewResult(successful=True)

        while True:
            cv2.imshow(window_name, frame)
            if _window_should_close(window_name, 1):
                return CameraPreviewResult(successful=True)

            success, frame = capture.read()
            if not success or frame is None:
                return CameraPreviewResult(
                    successful=False,
                    error="Camera stopped providing frames.",
                )
    except (cv2.error, TypeError, ValueError) as error:
        return CameraPreviewResult(
            successful=False,
            error=f"Preview failed: {error}",
        )
    finally:
        capture.release()
        cv2.destroyAllWindows()


def launch_camera_preview(
    camera: Camera,
    mode: CameraPreviewMode,
) -> CameraPreviewResult:
    """Launch a child process whose main thread owns the OpenCV window."""
    command = [
        sys.executable,
        "-m",
        "detect_objects.opencv_preview.camera_preview",
        "--index",
        str(camera.info.index),
        "--backend",
        str(camera.info.backend),
        "--name",
        camera.info.name,
        "--mode",
        mode.value,
    ]

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as error:
        return CameraPreviewResult(
            successful=False,
            error=f"Could not launch preview: {error}",
        )

    if completed.returncode == 0:
        return CameraPreviewResult(successful=True)

    error = completed.stderr.strip() or completed.stdout.strip()
    return CameraPreviewResult(
        successful=False,
        error=error or f"Preview exited with status {completed.returncode}.",
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the private command-line interface used by the launcher."""
    parser = argparse.ArgumentParser(description="Open an OpenCV camera preview.")
    parser.add_argument("--index", type=int, required=True)
    parser.add_argument("--backend", type=int, required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument(
        "--mode",
        choices=[mode.value for mode in CameraPreviewMode],
        required=True,
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the OpenCV preview inside the child process."""
    args = build_parser().parse_args(argv)
    result = show_camera_preview(
        index=args.index,
        backend=args.backend,
        name=args.name,
        mode=CameraPreviewMode(args.mode),
    )
    if result.successful:
        return 0

    print(result.error or "Camera preview failed.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
