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

## 카메라 인덱스 사용법

OpenCV는 컴퓨터에 연결된 각 카메라를 `0`, `1`, `2` 같은 정수 인덱스로
구분합니다. 일반적으로 내장 카메라는 `0`이지만, USB 카메라나 가상 카메라가
연결되어 있으면 인덱스가 달라질 수 있습니다.

먼저 사용 가능한 카메라 인덱스를 찾습니다.

```bash
python camera_cv/list_cameras.py
```

기본적으로 인덱스 `0`부터 `9`까지 검사합니다. 검사 범위나 프레임 읽기 재시도
횟수를 변경하려면 다음 옵션을 사용합니다.

```bash
python camera_cv/list_cameras.py --max-index 15 --attempts 20
```

출력에서 `available`로 표시된 인덱스를 `--camera-index`에 전달합니다. 예를 들어
카메라 `1`을 사용하려면 다음과 같이 실행합니다.

```bash
python camera_cv/camera.py --camera-index 1
```

여러 운영체제에서 카메라와 실행 환경 정보를 JSON으로 확인하려면 다음 명령을
사용할 수도 있습니다.

```bash
python camera_tools/find_cameras.py --start-index 0 --max-index 9
```

카메라가 검색되지 않으면 다른 애플리케이션이 카메라를 사용 중인지 확인하고,
운영체제 설정에서 터미널 또는 Python에 카메라 접근 권한이 허용되어 있는지
확인하세요.
