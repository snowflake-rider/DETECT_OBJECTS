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
        self.__thread_event = thread_event or threading.Event()
        self.__yolo_world_manager: YOLO_World_Manager = None
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
            self.__yolo_world_manager = YOLO_World_Manager()
            self.__yolo_world_manager.load()
            self.__yolo_world_manager.cache_class_embeddings(self.__supported_classes)
            self.__yolo_world_manager.activate_cached_classes(self.__classes)
        except Exception as e:
            print(e)
            self._gc_resource()
            raise RuntimeError("error occured while loading YOLO World Module\n")

    def _apply_latest_classes(self) -> None:
        """Apply the newest class request by swapping cached embeddings."""
        if self.__class_names_queue is None:
            return

        latest_request = None
        while True:
            try:
                latest_request = self.__class_names_queue.get_nowait()
            except queue.Empty:
                break

        if latest_request is None:
            return

        new_classes, requested_at = latest_request
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
            is_success, frame = self.__manager_obj.read()
            if not is_success:
                print("cannot read frame")
                break
            # Apply embeddings between frames, never during predict().
            self._apply_latest_classes()
            frame_height, frame_width = frame.shape[:2]
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

            cv2.imshow("Camera", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
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
