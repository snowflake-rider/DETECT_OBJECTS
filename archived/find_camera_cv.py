import cv2


def find_available_camera_indexes(max_index: int = 10) -> list[int]:
    available_indexes = []

    for index in range(max_index):
        cap = cv2.VideoCapture(index, cv2.CAP_AVFOUNDATION)

        if not cap.isOpened():
            print(f"[FAIL] index={index}: 열리지 않음")
            cap.release()
            continue

        success = False

        # 첫 프레임이 바로 안 오는 경우가 있어 여러 번 시도
        for _ in range(10):
            ret, frame = cap.read()

            if ret and frame is not None and frame.size > 0:
                success = True
                break

        if success:
            height, width = frame.shape[:2]
            print(f"[OK] index={index}: {width}x{height}")
            available_indexes.append(index)
        else:
            print(f"[FAIL] index={index}: 열렸지만 프레임 읽기 실패")

        cap.release()

    return available_indexes


indexes = find_available_camera_indexes()
print("사용 가능한 OpenCV 인덱스:", indexes)
