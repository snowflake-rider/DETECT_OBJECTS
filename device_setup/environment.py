from __future__ import annotations  # Delays type-hint evaluation.

import json
import platform  # System and OS information.
from pathlib import Path  # File-system paths.

# from typing import Any, Sequence  # Type-hint helpers.
from dataclasses import asdict, dataclass
from cv2_enumerate_cameras import enumerate_cameras
import subprocess
import sys
# Exposes environment settings (mac, windows, raspberry pi, etc)


@dataclass(frozen=True)
class Environment:
    os: str
    release: str
    machine: str
    python: str
    rpi: str | None = None

    def __str__(self) -> str:
        """returns a json-format string for Environment."""
        return json.dumps(self.as_dict(), ensure_ascii=False)

    # A class method can create an Environment before an instance exists.
    # ``cls`` refers to Environment (or a subclass), making this an alternative constructor.
    @classmethod
    def detect(cls) -> Environment:
        """Read the details from the machine"""
        # Calling cls(...) creates and returns a new Environment instance.
        return cls(
            os=platform.system() or "Unknown",
            release=platform.release(),
            machine=platform.machine(),
            python=platform.python_version(),
            # TODO: get_raspberry_pi_model() — 파이 연결하면 채운다.
            #       그때까지는 어느 보드든 None.
            rpi=None,
        )

    def as_dict(self) -> dict[str, str | None]:
        """Return a plain dict for the JSON report."""
        return asdict(self)

    def find_camera(self):

        # camera_table = subprocess.run(
        #     [sys.executable, "-m", "cv2_enumerate_cameras"],
        #     capture_output=True,
        #     text=True,
        #     check=True,
        # )
        # print(camera_table.stdout)
        try:
            cameras = enumerate_cameras()
            for camera_info in cameras:
                print(
                    f"Camera Info: {camera_info.index}-{camera_info.name}-{camera_info.path}-{camera_info.vid}-{camera_info.pid}-{camera_info.backend}"
                )

        except Exception as e:
            print(e)


if __name__ == "__main__":
    env = Environment.detect()
    print(env)
    env.find_camera()
    # for camera_info in enumerate_cameras():
    #     print(
    #         f"Camera Info: {camera_info.index}-{camera_info.name}-{camera_info.path}-{camera_info.vid}-{camera_info.pid}-{camera_info.backend}"
    #     )
