"""Discover cameras and store a selected camera."""

from __future__ import annotations

import platform

import cv2
from cv2_enumerate_cameras import enumerate_cameras, supported_backends
from cv2_enumerate_cameras.camera_info import CameraInfo

# CameraInfo contains the information returned by cv2_enumerate_cameras:
# index = number OpenCV uses, name = readable device name, path = device path,
# vid/pid = optional USB IDs, and backend = API used to access the camera.


class Camera:
    """Store the camera selected for one application run."""

    def __init__(self, camera_info: CameraInfo) -> None:
        """Save the selected camera information for this program run."""
        # Nothing is written to a file, so this selection disappears when the
        # program ends and the user will be asked to choose again next time.
        self.info = camera_info

    @staticmethod
    def get_backend() -> int:
        """Select the preferred OpenCV backend for the current OS."""
        # A backend is the bridge between OpenCV and the operating system's
        # camera API: AVFoundation on macOS, MSMF on Windows, and V4L2 on Linux.
        backend = {
            "Darwin": cv2.CAP_AVFOUNDATION,
            "Windows": cv2.CAP_MSMF,
            "Linux": cv2.CAP_V4L2,
            # TODO: Raspberry Pi
        }.get(platform.system(), cv2.CAP_ANY)

        # The enumeration package may not support OpenCV's preferred backend.
        # If that happens, use the first backend the package says it supports.
        if backend not in supported_backends:
            if not supported_backends:
                raise RuntimeError("No supported camera backends were found.")

            backend = supported_backends[0]

        return backend

    @classmethod
    def list_devices(cls) -> list[CameraInfo]:
        """Return cameras available through the preferred OpenCV backend."""
        backend = cls.get_backend()

        # Passing a backend gives us normal camera indexes such as 0 and 1.
        # Without it, some systems return indexes containing a backend offset.
        return list(enumerate_cameras(backend))
