"""Find cameras on macOS, Windows, Linux, and Raspberry Pi.

``CameraFinder`` detects the current environment, selects a suitable OpenCV
backend, probes a configurable range of camera indexes, and outputs JSON.
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from pathlib import Path
from typing import Any, Sequence

import cv2


class CameraFinder:
    """Discover cameras and report the environment in which they were found."""

    BACKENDS = {
        "any": ("CAP_ANY", "OpenCV automatic"),
        "avfoundation": ("CAP_AVFOUNDATION", "AVFoundation"),
        "msmf": ("CAP_MSMF", "Microsoft Media Foundation"),
        "dshow": ("CAP_DSHOW", "DirectShow"),
        "v4l2": ("CAP_V4L2", "Video4Linux2"),
    }

    def __init__(
        self,
        start_index: int = 0,
        max_index: int = 9,
        attempts: int = 5,
        retry_delay: float = 0.1,
        backend: str = "auto",
        environment: dict[str, Any] | None = None,
    ) -> None:
        """Configure the index range, retry behavior, and capture backend."""
        if start_index < 0 or max_index < start_index:
            raise ValueError("camera index range is invalid")
        if attempts < 1 or retry_delay < 0:
            raise ValueError(
                "attempts must be positive and retry_delay cannot be negative"
            )

        # Camera indexes are inclusive, so 0..9 probes ten possible devices.
        self.start_index, self.max_index = start_index, max_index

        # A camera may open before its first frame is ready. These settings
        # control how often and how quickly the finder retries reading a frame.
        self.attempts, self.retry_delay = attempts, retry_delay

        # "auto" selects a native backend for the detected operating system.
        self.requested_backend = backend

        # A custom environment is useful when the caller already knows the
        # platform details. Otherwise, detect them from the current system.
        self.environment = environment or self.get_environment()

        self.backend, self.backend_label = self._choose_backend(backend)

    @staticmethod
    def get_raspberry_pi_model(
        paths: Sequence[Path] = (
            Path("/proc/device-tree/model"),
            Path("/sys/firmware/devicetree/base/model"),
        ),
    ) -> str | None:
        """Return the Raspberry Pi model from Linux device-tree files."""
        for path in paths:
            try:
                model = path.read_text(encoding="utf-8").replace("\x00", "").strip()
            except (OSError, UnicodeError):
                continue

            if "raspberry pi" in model.lower():
                return model

        return None

    @classmethod
    def get_environment(cls) -> dict[str, Any]:
        """Return the OS, CPU, Python version, and Raspberry Pi model."""
        pi_model = cls.get_raspberry_pi_model()
        return {
            "os": platform.system() or "Unknown",
            "release": platform.release(),
            "machine": platform.machine(),
            "python": platform.python_version(),
            "raspberry_pi": pi_model,
        }

    def _choose_backend(self, name: str) -> tuple[int, str]:
        """Choose an OpenCV backend automatically or by its explicit name."""
        if name == "auto":
            name = {
                "Darwin": "avfoundation",
                "Windows": "msmf",
                "Linux": "v4l2",
            }.get(self.environment["os"], "any")

        constant_name, label = self.BACKENDS[name]
        if not hasattr(cv2, constant_name):
            raise RuntimeError(f"OpenCV does not provide {constant_name}.")

        return getattr(cv2, constant_name), label

    def _probe(self, index: int) -> dict[str, Any]:
        """Probe one index and return its status, resolution, and FPS."""
        capture = cv2.VideoCapture(index, self.backend)

        try:
            if not capture.isOpened():
                return {
                    "index": index,
                    "available": False,
                    "status": "could not open",
                }

            frame = None

            # USB and Raspberry Pi cameras may need time before the first frame.
            for attempt in range(self.attempts):
                success, candidate = capture.read()
                if success and candidate is not None and candidate.size > 0:
                    frame = candidate
                    break
                if attempt < self.attempts - 1 and self.retry_delay > 0:
                    time.sleep(self.retry_delay)

            if frame is None:
                return {
                    "index": index,
                    "available": False,
                    "status": f"no frame after {self.attempts} attempt(s)",
                }

            height, width = frame.shape[:2]
            fps = float(capture.get(cv2.CAP_PROP_FPS))

            try:
                active_backend = capture.getBackendName()
            except (AttributeError, RuntimeError):
                active_backend = self.backend_label

            return {
                "index": index,
                "available": True,
                "status": "available",
                "width": int(width),
                "height": int(height),
                "fps": round(fps, 2) if fps > 0 else None,
                "backend": active_backend,
            }
        finally:
            # Release every probe before attempting to open the next index.
            capture.release()

    def first_available(self) -> int | None:
        """Return the lowest usable camera index, or ``None`` if there is none.

        Probing stops at the first success, so callers that only need a camera
        to open do not pay for the whole index range.
        """
        for index in range(self.start_index, self.max_index + 1):
            if self._probe(index)["available"]:
                return index

        return None

    def scan(self) -> dict[str, Any]:
        """Probe the configured index range and return a report dictionary."""
        started = time.monotonic()
        probes = [
            self._probe(index) for index in range(self.start_index, self.max_index + 1)
        ]

        return {
            "environment": self.environment,
            "backend": self.backend_label,
            "index_range": [self.start_index, self.max_index],
            "attempts": self.attempts,
            "cameras": [probe for probe in probes if probe["available"]],
            "probes": probes,
            "duration_seconds": round(time.monotonic() - started, 3),
        }


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Find cameras and report the current environment."
    )
    parser.add_argument("--start-index", type=int, default=0)
    parser.add_argument("--max-index", type=int, default=9)
    parser.add_argument("--attempts", type=int, default=5)
    parser.add_argument("--retry-delay", type=float, default=0.1)
    parser.add_argument(
        "--backend",
        choices=("auto", *CameraFinder.BACKENDS),
        default="auto",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Create a finder from CLI arguments, scan, and print the report."""

    # Namespace(start_index=0, max_index=9, attempts=5, retry_delay=0.1, backend='auto')
    args = build_parser().parse_args(argv)

    try:
        finder = CameraFinder(
            start_index=args.start_index,
            max_index=args.max_index,
            attempts=args.attempts,
            retry_delay=args.retry_delay,
            backend=args.backend,
        )
        report = finder.scan()
    except (RuntimeError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    # JSON is the only output format so other programs can parse it reliably.
    print(json.dumps(report, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
