"""Run real-time YOLO-World object detection on a local camera stream.

The camera manager opens the camera index supplied on the command line,
captures frames through OpenCV, and draws YOLO-World predictions until the
user presses ``q``.
"""

import argparse
import cv2
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))

from models.yolo_world_module import YOLO_World_Manager


class Camera_Manager:
    """Coordinate camera capture, inference, and resource cleanup."""

    def __init__(self, camera_index):
        """Open the requested camera and configure detectable classes."""
        # Camera indexes depend on the computer and its connected devices, so
        # the caller chooses the index instead of this class hard-coding it.
        self.__camera_index = camera_index
        self.__backend = self._select_backend()
        self.__manager_obj = cv2.VideoCapture(
            self.__camera_index,
            self.__backend,
        )
        self.__classes = [
            "smartphone",
            "wristwatch",
            "keyboard",
            "person",
        ]

    def _select_backend(self) -> int:
        """Choose the native OpenCV video backend for the current OS."""
        os_name = platform.system()
        print(f"os name : {os_name}")
        backend_map = {
            "Darwin": cv2.CAP_AVFOUNDATION,  # macOS
            "Linux": cv2.CAP_V4L2,  # Linux
            "Windows": cv2.CAP_MSMF,  # Windows 10/11
        }
        return backend_map.get(os_name, cv2.CAP_ANY)

    def start_record(self):
        """Start the detection preview and run until ``q`` or a read failure."""
        if not self.__manager_obj.isOpened():
            self._gc_resource()
            raise RuntimeError(f"camera index {self.__camera_index} is unavailable!")
        try:
            yolo_manager = YOLO_World_Manager(confidence=0.35)
            yolo_manager.load()
            yolo_manager.set_classes(self.__classes)
        except Exception as e:
            print(e)
            self._gc_resource()
            return
        while True:
            is_success, frame = self.__manager_obj.read()
            if not is_success:
                print("cannot read frame")
                break
            frame_height, frame_width = frame.shape[:2]
            boxes, names = yolo_manager.predict(frame=frame)

            # YOLO returns normalized coordinates; OpenCV drawing functions
            # require integer pixel coordinates in the current frame.
            for box in boxes:
                x1, y1, x2, y2 = box.xyxyn[0].tolist()
                x1 = int(x1 * frame_width)
                y1 = int(y1 * frame_height)
                x2 = int(x2 * frame_width)
                y2 = int(y2 * frame_height)
                confidence = float(box.conf)
                class_id = int(box.cls[0].item())
                class_name = names[class_id]
                cv2.rectangle(
                    frame,
                    (x1, y1),
                    (x2, y2),
                    (0, 255, 0),
                    2,
                )
                confidence = float(box.conf[0].item())
                label = f"confidence:{confidence} , name: {class_name}"
                cv2.putText(
                    frame,
                    label,
                    (x1, y1 + 30),
                    cv2.FONT_HERSHEY_PLAIN,
                    2,
                    (0, 0, 255),
                    2,
                )

            cv2.imshow("Camera", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
        yolo_manager.close()
        self._gc_resource()

    def _gc_resource(self):
        """Release the capture device and close all OpenCV preview windows."""
        if self.__manager_obj is not None:
            self.__manager_obj.release()
        cv2.destroyAllWindows()


def parse_args():
    """Read the machine-specific camera index from the command line."""
    parser = argparse.ArgumentParser(
        description="Run object detection with a selected camera.",
    )
    parser.add_argument(
        "--camera-index",
        type=int,
        required=True,
        help="OpenCV camera index to open, such as 0 or 1.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    try:
        camera_manager = Camera_Manager(args.camera_index)
        camera_manager.start_record()
    except RuntimeError as e:
        print(e)
