"""Probe OpenCV camera indexes and report which devices can return frames.

This is the portable camera-discovery CLI.  Backend selection is based on the
host operating system, while the index range and retry count are configurable.
"""

import argparse
import platform
import time

import cv2


def get_backend() -> int:
    """Return the OpenCV capture backend best suited to the current OS."""
    backend_by_os = {
        "Darwin": cv2.CAP_AVFOUNDATION,
        "Linux": cv2.CAP_V4L2,
        "Windows": cv2.CAP_MSMF,
    }
    return backend_by_os.get(platform.system(), cv2.CAP_ANY)


def read_frame(camera: cv2.VideoCapture, attempts: int) -> object | None:
    """Read a frame, retrying briefly while a camera finishes warming up."""
    for _ in range(attempts):
        success, frame = camera.read()

        if success:
            return frame

        time.sleep(0.1)

    return None


def find_cameras(max_index: int, attempts: int) -> list[int]:
    """Return camera indexes that open successfully and produce a frame."""
    backend = get_backend()
    available_indexes = []

    print(f"OS: {platform.system()}")
    print(f"카메라 인덱스 0~{max_index} 검사 중...\n")

    for index in range(max_index + 1):
        camera = cv2.VideoCapture(index, backend)

        try:
            if not camera.isOpened():
                print(f"[{index}] unavailable")
                continue

            frame = read_frame(camera, attempts)
            if frame is None:
                print(f"[{index}] opened, but cannot read frames")
                continue

            height, width = frame.shape[:2]
            fps = camera.get(cv2.CAP_PROP_FPS)
            available_indexes.append(index)

            print(
                f"[{index}] available "
                f"({width}x{height}, reported FPS: {fps:.1f})"
            )
        finally:
            camera.release()

    return available_indexes


def main() -> None:
    """Parse CLI options, scan camera indexes, and print a summary."""
    parser = argparse.ArgumentParser(
        description="사용 가능한 OpenCV 카메라 인덱스를 찾습니다."
    )
    parser.add_argument(
        "--max-index",
        type=int,
        default=9,
        help="검사할 마지막 카메라 인덱스 (기본값: 9)",
    )
    parser.add_argument(
        "--attempts",
        type=int,
        default=10,
        help="각 카메라의 프레임 읽기 재시도 횟수 (기본값: 10)",
    )
    args = parser.parse_args()

    if args.max_index < 0:
        parser.error("--max-index는 0 이상이어야 합니다.")

    if args.attempts < 1:
        parser.error("--attempts는 1 이상이어야 합니다.")

    available_indexes = find_cameras(args.max_index, args.attempts)

    if available_indexes:
        indexes = ", ".join(map(str, available_indexes))
        print(f"\n사용 가능한 카메라 인덱스: {indexes}")
    else:
        print("\n사용 가능한 카메라를 찾지 못했습니다.")


if __name__ == "__main__":
    main()
