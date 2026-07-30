# detect_objects

OpenCV 카메라 영상에서 YOLO-World로 객체를 탐지하는 실험용 Python
프로젝트입니다.

## 주요 파일

- `camera_cv/camera.py`: 카메라 영상을 받아 실시간 객체 탐지를 실행합니다.
- `camera_cv/list_cameras.py`: 운영체제에 맞는 OpenCV 백엔드로 사용 가능한
  카메라 인덱스를 찾습니다.
- `camera_cv/camera_test.py`: 모델 없이 카메라 프리뷰만 확인합니다.
- `camera_tools/find_cameras.py`: 여러 운영체제에서 사용할 수 있는 카메라
  인덱스와 실행 환경을 JSON으로 확인합니다.
- `models/device_selector.py`: MPS, CUDA, CPU 순으로 추론 장치를 선택합니다.
- `models/yolo_world_module.py`: YOLO-World 모델의 로딩, 추론, 해제를 관리합니다.

## 실행 예시

```bash
python camera_cv/list_cameras.py
python camera_cv/camera_test.py
python camera_cv/camera.py --camera-index 0
python camera_tools/find_cameras.py
```

카메라 프리뷰에서는 `q`를 눌러 종료합니다.
