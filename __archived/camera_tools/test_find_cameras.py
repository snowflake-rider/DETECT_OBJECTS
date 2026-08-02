"""Tests for the cross-platform camera finder using fake camera hardware."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Import by package name so the tests run either from the project root
# (``python -m unittest discover``) or from this directory.
ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))

from camera_tools import find_cameras


class FakeFrame:
    """Provide the frame attributes used by the camera finder."""

    def __init__(self, height: int, width: int) -> None:
        self.shape = (height, width, 3)
        self.size = height * width * 3


class FakeCapture:
    """Simulate an OpenCV VideoCapture."""

    def __init__(self, opened: bool, reads: list, fps: float = 0) -> None:
        self.opened = opened
        self.reads = iter(reads)
        self.fps = fps
        self.released = False

    def isOpened(self) -> bool:
        return self.opened

    def read(self) -> tuple:
        return next(self.reads, (False, None))

    def get(self, property_id: int) -> float:
        return self.fps

    def getBackendName(self) -> str:
        return "FAKE"

    def release(self) -> None:
        self.released = True


class FakeCV2:
    """Provide the OpenCV API used by the module."""

    CAP_ANY = 0
    CAP_AVFOUNDATION = 1
    CAP_MSMF = 2
    CAP_DSHOW = 3
    CAP_V4L2 = 4
    CAP_PROP_FPS = 5

    def __init__(self, scenarios: dict[int, dict]) -> None:
        self.scenarios = scenarios
        self.captures = []

    def VideoCapture(self, index: int, backend: int) -> FakeCapture:
        scenario = self.scenarios.get(index, {"opened": False, "reads": []})
        capture = FakeCapture(**scenario)
        self.captures.append(capture)
        return capture


def environment(system: str, pi_model: str | None = None) -> dict:
    """Return stable environment information for tests."""
    return {
        "os": system,
        "release": "test",
        "machine": "arm64",
        "python": "3.11",
        "raspberry_pi": pi_model,
    }


class FindCamerasTests(unittest.TestCase):
    """Test backend selection, Pi detection, probing, and cleanup."""

    def test_auto_backend_for_each_os(self) -> None:
        cases = {
            "Darwin": FakeCV2.CAP_AVFOUNDATION,
            "Windows": FakeCV2.CAP_MSMF,
            "Linux": FakeCV2.CAP_V4L2,
        }

        for system, expected in cases.items():
            with self.subTest(system=system):
                fake_cv2 = FakeCV2({})
                with patch.object(find_cameras, "cv2", fake_cv2):
                    finder = find_cameras.CameraFinder(
                        environment=environment(system),
                    )
                self.assertEqual(finder.backend, expected)

    def test_raspberry_pi_model(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "model"
            path.write_bytes(b"Raspberry Pi 5 Model B\x00")
            self.assertEqual(
                find_cameras.CameraFinder.get_raspberry_pi_model((path,)),
                "Raspberry Pi 5 Model B",
            )

    def test_scan_finds_camera_after_retry_and_releases_resources(self) -> None:
        fake_cv2 = FakeCV2(
            {
                0: {"opened": False, "reads": []},
                1: {
                    "opened": True,
                    "reads": [
                        (False, None),
                        (True, FakeFrame(720, 1280)),
                    ],
                    "fps": 30,
                },
            }
        )

        with patch.object(find_cameras, "cv2", fake_cv2):
            finder = find_cameras.CameraFinder(
                start_index=0,
                max_index=1,
                attempts=2,
                retry_delay=0,
                environment=environment("Linux", "Raspberry Pi 5 Model B"),
            )
            report = finder.scan()

        self.assertEqual([camera["index"] for camera in report["cameras"]], [1])
        self.assertEqual(report["cameras"][0]["width"], 1280)
        self.assertTrue(all(capture.released for capture in fake_cv2.captures))

    def test_first_available_stops_at_the_first_usable_index(self) -> None:
        fake_cv2 = FakeCV2(
            {
                1: {"opened": True, "reads": [(True, FakeFrame(480, 640))]},
                2: {"opened": True, "reads": [(True, FakeFrame(480, 640))]},
            }
        )

        with patch.object(find_cameras, "cv2", fake_cv2):
            finder = find_cameras.CameraFinder(
                max_index=5,
                attempts=1,
                retry_delay=0,
                environment=environment("Darwin"),
            )
            index = finder.first_available()

        self.assertEqual(index, 1)
        # Indexes 0 and 1 only: probing must not continue past the first hit.
        self.assertEqual(len(fake_cv2.captures), 2)

    def test_first_available_without_cameras(self) -> None:
        fake_cv2 = FakeCV2({})

        with patch.object(find_cameras, "cv2", fake_cv2):
            finder = find_cameras.CameraFinder(
                max_index=2,
                environment=environment("Linux"),
            )
            self.assertIsNone(finder.first_available())

    def test_invalid_range(self) -> None:
        with self.assertRaises(ValueError):
            find_cameras.CameraFinder(
                start_index=2,
                max_index=1,
                environment=environment("Darwin"),
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
