"""Run real-time YOLO-World object detection on a local camera stream.

The camera manager opens the camera index supplied on the command line,
captures frames through OpenCV, and draws YOLO-World predictions until the
user presses ``q``.
"""

import argparse
import cv2
import platform
import threading
import queue
import time
from typing import TYPE_CHECKING

from ..models import DEFAULT_VISION_MODEL_ID
from ..models.factory import create_vision_manager

CLASSIC_WINDOW_NAME = "ODIA Classic — press Q or Esc to quit"

if TYPE_CHECKING:
    from ..models.yolo_world_module import YOLO_World_Manager


class Camera_Manager:
    """Coordinate camera capture, inference, and resource cleanup."""

    def __init__(
        self,
        camera_index,
        thread_event: threading.Event = None,
        class_names_queue: queue.Queue[tuple[list[str], float]] | None = None,
        supported_classes: list[str] | None = None,
        camera_backend: int | None = None,
        vision_model_id: str = DEFAULT_VISION_MODEL_ID,
    ):
        """Open the requested camera and configure detectable classes."""
        # Camera indexes depend on the computer and its connected devices, so
        # the caller chooses the index instead of this class hard-coding it.
        self.__camera_index = camera_index
        self.__backend = (
            camera_backend if camera_backend is not None else self._select_backend()
        )
        self.__manager_obj = cv2.VideoCapture(
            self.__camera_index,
            self.__backend,
        )
        self.__classes = [
            "cell phone",
            "clock",
            "keyboard",
            "person",
        ]
        self.__supported_classes = supported_classes or self.__classes
        self.__vision_model_id = vision_model_id
        self.__thread_event = thread_event or threading.Event()
        self.__yolo_world_manager: YOLO_World_Manager | None = None
        self.__class_names_queue = class_names_queue

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

    # Yolo world model
    def load_model(self):
        try:
            self.__yolo_world_manager = create_vision_manager(self.__vision_model_id)
            self.__yolo_world_manager.load()
            self.__yolo_world_manager.cache_class_embeddings(self.__supported_classes)
            self.__yolo_world_manager.activate_cached_classes(self.__classes)
        except Exception as e:
            print(e)
            self._gc_resource()
            raise RuntimeError("error occured while loading YOLO World Module\n")

    @property
    def inference_device_name(self) -> str:
        """Return the device name selected by the loaded vision model."""
        if self.__yolo_world_manager is None:
            raise RuntimeError("The vision model has not been loaded.")
        return self.__yolo_world_manager.device_name

    def _apply_latest_classes(self) -> None:
        """Apply the newest class request by swapping cached embeddings."""
        # ⭐ VOICE MAILBOX PROCESS
        # The voice thread puts new instructions here, for example:
        #     (["cup"], requested_at)
        # The camera thread checks the mailbox before detecting each frame.
        # The queue stores only new instructions, not YOLO's current setting.

        # Some camera uses may not have a voice-request mailbox.
        if self.__class_names_queue is None:
            return

        # Start with no request received for this camera frame.
        latest_request = None

        # get_nowait() removes one request immediately; it never waits for one.
        # If several exist, the last one removed is the newest one.
        while True:
            try:
                latest_request = self.__class_names_queue.get_nowait()
            except queue.Empty:
                # Empty is normal. It means "no new voice instruction."
                # It does not erase the classes YOLO is already detecting.
                break

        # Example: YOLO was detecting ["cup"] and the queue is now empty.
        # Keep detecting ["cup"] until voice sends another instruction.
        if latest_request is None:
            return

        # Separate the queue item into its class list and creation time.
        new_classes, requested_at = latest_request

        # A new instruction exists, so replace YOLO's current classes.
        # Example: ["cup"] becomes ["dog"]. Future frames detect dogs.
        self.__yolo_world_manager.activate_cached_classes(new_classes)
        self.__classes = new_classes
        print(
            f"클래스 임베딩 변경 완료: classes={self.__classes}, "
            f"device={self.__yolo_world_manager.device}"
        )
        elapsed_seconds = time.perf_counter() - requested_at
        print(
            f"[성능] 클래스 임베딩 변경 완료: {elapsed_seconds * 1000:.2f} ms "
            f"(classes={new_classes})"
        )

    # process start, end logic
    def start_record(self):
        """Start the detection preview and run until ``q`` or a read failure."""
        if not self.__manager_obj.isOpened():
            self._gc_resource()
            raise RuntimeError(f"camera index {self.__camera_index} is unavailable!")

        while not self.__thread_event.is_set():
            # Every loop follows this order:
            # 1. Read one camera frame.
            # 2. Check the voice mailbox.
            # 3. Apply new classes if a request exists.
            # 4. Run YOLO with the current classes.
            is_success, frame = self.__manager_obj.read()
            if not is_success:
                print("cannot read frame")
                break

            # Check the voice mailbox before running YOLO on this frame.
            # Apply changes between frames, never during predict().
            self._apply_latest_classes()
            frame_height, frame_width = frame.shape[:2]

            # If the mailbox was empty, YOLO still remembers its old classes.
            boxes, names = self.__yolo_world_manager.predict(frame=frame)
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

            cv2.imshow(CLASSIC_WINDOW_NAME, frame)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), ord("Q"), 27):
                break

            try:
                if (
                    cv2.getWindowProperty(
                        CLASSIC_WINDOW_NAME,
                        cv2.WND_PROP_VISIBLE,
                    )
                    < 1
                ):
                    break
            except cv2.error:
                break

        self._gc_resource()

    def _gc_resource(self):
        """Release the capture device and close all OpenCV preview windows."""
        if self.__manager_obj is not None:
            self.__manager_obj.release()
        if self.__yolo_world_manager is not None:
            self.__yolo_world_manager.close()
        if (self.__thread_event is not None) and (
            self.__thread_event.is_set() == False
        ):
            self.__thread_event.set()
        cv2.destroyAllWindows()

    def unload(self):
        self._gc_resource()


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
