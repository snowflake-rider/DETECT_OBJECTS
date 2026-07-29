import cv2

backend = cv2.CAP_AVFOUNDATION

for index in range(10):
    cap = cv2.VideoCapture(index, backend)

    if cap.isOpened():
        success, frame = cap.read()

        if success and frame is not None:
            height, width = frame.shape[:2]
            print(
                f"[OK] index={index}, "
                f"resolution={width}x{height}, "
                f"backend={cap.getBackendName()}"
            )
        else:
            print(f"[OPENED BUT READ FAILED] index={index}")
    else:
        print(f"[FAILED] index={index}")

    cap.release()
