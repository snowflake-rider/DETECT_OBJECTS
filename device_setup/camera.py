"""Find an attached camera, let the user choose it, and show a preview."""

from __future__ import annotations

import platform

import cv2
from cv2_enumerate_cameras import enumerate_cameras, supported_backends
from cv2_enumerate_cameras.camera_info import CameraInfo
from rich.console import Console
from rich.prompt import Confirm, IntPrompt
from rich.table import Table

# CameraInfo contains the information returned by cv2_enumerate_cameras:
# index = number OpenCV uses, name = readable device name, path = device path,
# vid/pid = optional USB IDs, and backend = API used to access the camera.


class Camera:
    """Store a selected camera and provide an OpenCV preview."""

    # Reuse one Rich console so every message has consistent formatting.
    console = Console()

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
    def choose(cls) -> CameraInfo | None:
        """Display available cameras and let the user select one."""
        cameras = cls.list_devices()

        if not cameras:
            cls.console.print("[yellow]No available cameras were found.[/yellow]")
            return None

        # Build a readable terminal table from the detected camera information.
        table = Table(title="Available Cameras")
        table.add_column("Choice", justify="right", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Backend")

        for choice, camera in enumerate(cameras, start=1):
            # Convert a value such as 1200 into a name such as AVFOUNDATION.
            backend_name = cv2.videoio_registry.getBackendName(camera.backend)

            table.add_row(
                str(choice),
                camera.name,
                backend_name,
            )

        cls.console.print(table)

        # Keep asking until the user enters a valid menu number or cancels.
        while True:
            choice = IntPrompt.ask(
                f"Choose a camera [1-{len(cameras)}], or 0 to cancel",
                default=0,
            )

            if choice == 0:
                return None

            if 1 <= choice <= len(cameras):
                # Menu choices start at 1, while list positions start at 0.
                return cameras[choice - 1]

            cls.console.print(
                f"[red]Enter a number between 1 and {len(cameras)}.[/red]"
            )

    def test(self) -> bool:
        """Open a live OpenCV preview using the saved camera information."""
        # Both values must match those returned by enumerate_cameras().
        capture = cv2.VideoCapture(self.info.index, self.info.backend)

        try:
            if not capture.isOpened():
                self.console.print(f"[red]Could not open '{self.info.name}'.[/red]")
                return False

            self.console.print(
                "[green]Camera opened. Press Q or Escape to close.[/green]"
            )

            # Read and display frames until the camera fails or the user exits.
            while True:
                success, frame = capture.read()

                if not success or frame is None:
                    self.console.print("[red]Could not read a frame.[/red]")
                    return False

                cv2.imshow(self.info.name, frame)

                # Handle keyboard input for the OpenCV preview window:
                # press "q" → waitKey(1) returns 113 → 113 & 0xFF → key is 113
                # press Esc → waitKey(1) returns 27 → 27 & 0xFF → key is 27
                # press nothing → waitKey(1) returns -1 → -1 & 0xFF → key is 255
                # key is 113 or 27 → condition is True → exit the preview
                key = cv2.waitKey(1) & 0xFF

                if key in (ord("q"), 27):
                    return True
        finally:
            # Always release the hardware and close windows, even after an error.
            capture.release()
            cv2.destroyAllWindows()

    @classmethod
    def setup(cls) -> Camera | None:
        """Save the selected camera and optionally run its preview."""
        selected_info = cls.choose()

        if selected_info is None:
            cls.console.print("[yellow]No camera selected.[/yellow]")
            return None

        # Record the user's choice immediately. Testing is optional and does not
        # decide whether this Camera object keeps the selected CameraInfo.
        camera = cls(selected_info)
        cls.console.print(f"[green]Selected '{camera.info.name}'.[/green]")

        should_test = Confirm.ask(
            f"Do you want to test '{selected_info.name}'?",
            default=False,
        )

        if not should_test:
            cls.console.print("[yellow]Skipping camera test.[/yellow]")
            return camera

        if not camera.test():
            cls.console.print("[red]Camera test failed.[/red]")
            return None

        cls.console.print("[green]Camera test completed.[/green]")
        return camera

    @classmethod
    def list_devices(cls) -> list[CameraInfo]:
        """Return cameras available through the preferred OpenCV backend."""
        backend = cls.get_backend()

        # Passing a backend gives us normal camera indexes such as 0 and 1.
        # Without it, some systems return indexes containing a backend offset.
        return list(enumerate_cameras(backend))


if __name__ == "__main__":
    # This block runs only when camera.py is executed directly.
    camera = Camera.setup()
