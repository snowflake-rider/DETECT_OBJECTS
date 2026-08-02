# detect_objects

OpenCV 카메라 영상에서 YOLO-World로 객체를 탐지하는 실험용 Python
프로젝트입니다.

## uv 환경 설정

이 프로젝트는 Python 3.11을 사용합니다. `uv`가 설치되어 있다면 다음 명령으로
프로젝트 전용 `.venv`를 만들고 잠긴 버전의 의존성을 설치할 수 있습니다.

```bash
uv sync --locked
```

환경을 직접 활성화하지 않고 실행하려면 각 명령 앞에 `uv run`을 붙입니다.

```bash
uv run python camera_cv/list_cameras.py
uv run python camera_cv/camera_test.py
uv run python camera_cv/camera.py --camera-index 0
uv run python -m tui.app
```

셸에서 환경을 활성화하려면 다음 명령을 사용합니다.

```bash
source .venv/bin/activate
```

## 주요 파일

- `camera_cv/camera.py`: 카메라 영상을 받아 실시간 객체 탐지를 실행합니다.
- `camera_cv/list_cameras.py`: 운영체제에 맞는 OpenCV 백엔드로 사용 가능한
  카메라 인덱스를 찾습니다.
- `camera_cv/camera_test.py`: 모델 없이 카메라 프리뷰만 확인합니다.
- `device_setup/`: UI와 독립적으로 카메라와 마이크를 검색하고 선택 정보를
  저장합니다.
- `tui/`: Textual 장치 선택 화면과 애플리케이션 셸을 제공합니다.
- `cli/`: 선택적으로 사용할 수 있는 Rich 기반 장치 설정 인터페이스입니다.
- `models/device_selector.py`: MPS, CUDA, CPU 순으로 추론 장치를 선택합니다.
- `models/model_config.py`: `config/models.toml`을 읽고 모델 설정과 가중치
  경로를 검증합니다.
- `models/yolo_world_module.py`: YOLO-World 모델의 로딩, 추론, 해제를 관리합니다.
- `models/sound/`: Apple SoundAnalysis를 사용하는 macOS 사운드 분류 백엔드와
  공통 결과 타입을 제공합니다.
- `config/models.toml`: 모델 가중치 경로와 추론 기본값을 저장합니다. 가중치
  경로는 이 TOML 파일을 기준으로 해석됩니다. Apple 내장 사운드 분류기는
  macOS가 관리하므로 별도의 가중치 경로가 필요하지 않습니다.
- `model_artifacts/`: 로컬 모델 가중치를 저장합니다. 가중치 파일은 Git에서
  제외됩니다.

## 실행 예시

```bash
python camera_cv/list_cameras.py
python camera_cv/camera_test.py
python camera_cv/camera.py --camera-index 0
python -m tui.app
python -m cli.device_setup
python -m models.sound /path/to/audio.wav
```

사운드 분류 명령은 macOS의 Apple SoundAnalysis를 사용합니다. 결과는 설정한
임계값을 통과한 `cat_meow`, `dog_bark`, 엔진, 경주차 소리를 시간 구간별로
출력합니다. 분석 구간, 겹침 비율, 레이블별 임계값은 `config/models.toml`에서
조정할 수 있습니다.

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

Textual 장치 설정 마법사를 실행하려면 다음 명령을 사용합니다.

```bash
python -m tui.app
```

마법사는 오디오 출력, 오디오 입력, 비디오 입력 순서로 진행됩니다. 먼저 출력
장치를 선택하고 고양이 울음 샘플을 들은 뒤 정상 재생 여부를 확인합니다. 다음으로
마이크를 선택하고 `Monitor`를 누른 뒤 "Hello"라고 말합니다. 녹음하는 동안
진행 막대와 dB 값이 실시간으로 갱신됩니다. `Done`으로 녹음을 끝낸 뒤
`Playback`을 눌러 선택한 출력 장치로 녹음을 확인합니다.

비디오 입력 단계에서는 `Start Camera Test`로 정지 이미지를 먼저 확인합니다.
이 테스트가 성공하면 `Start Streaming Test`가 활성화되어 실시간 영상을 별도로
확인할 수 있습니다. 각 OpenCV 창은 `q` 또는 Escape로 닫습니다. 두 테스트를 모두
마치고 사용자가 확인해야 다음 단계가 활성화되며 마지막 화면에 선택한 장치
이름이 대시보드로 표시됩니다.

카메라가 검색되지 않으면 다른 애플리케이션이 카메라를 사용 중인지 확인하고,
운영체제 설정에서 터미널 또는 Python에 카메라 접근 권한이 허용되어 있는지
확인하세요.
