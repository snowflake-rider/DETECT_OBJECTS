"""Display a raw camera preview to verify capture without loading a model.

Press ``q`` or Escape to close the preview.  Temporary read failures are
retried because some camera devices need time to begin delivering frames.
"""

import platform
import time

import cv2


def get_camera_backend() -> int:
    """Use AVFoundation on macOS and OpenCV's automatic backend elsewhere."""
    if platform.system() == "Darwin":
        return cv2.CAP_AVFOUNDATION

    return cv2.CAP_ANY


def main() -> None:
    """Open camera index 0 and display frames until the user exits."""
    camera = cv2.VideoCapture(0, get_camera_backend())

    if not camera.isOpened():
        raise RuntimeError("카메라를 열 수 없습니다.")

    print("카메라 초기화 중...")
    consecutive_failures = 0

    try:
        while True:
            success, frame = camera.read()

            if not success:
                consecutive_failures += 1

                if consecutive_failures >= 20:
                    raise RuntimeError("카메라 프레임을 읽을 수 없습니다.")

                time.sleep(0.05)
                continue

            consecutive_failures = 0
            cv2.imshow("Camera Test", frame)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):
                break
    finally:
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
