# 장치 설정(preflight) 모듈 설계서

앱을 켜기 전에 **머신 정보 + 카메라 + 마이크를 한 곳에서 확정**하는 모듈.
사용자가 장치를 고르면 **실제로 열어서 눈·귀로 확인**시키고, 확정된 설정을
JSON으로 남긴다. 여기서 오류가 없어야 본 앱이 돌아간다.

`camera_tools/find_cameras.py`(235줄)를 대체한다. 기존 출력과 호환 의무 없음.

작업 위치: `camera_tools/refactored/`

> 📛 다 만들면 디렉터리를 `devices/`로 옮기자. 카메라만 다루는 게 아니라
> `camera_tools`라는 이름이 더 이상 안 맞는다. (지금 옮기면 경로가 계속 바뀌니
> 마지막에.)

---

## 1. 흐름

```
$ python -m camera_tools.refactored.setup

환경
  Darwin 25.5.0 / arm64 / Python 3.11.14

카메라
  [0] FaceTime HD Camera
  [1] kafka-iphone Camera
  번호: 1
    → 미리보기 창이 열림. 확인했으면 q
  이 카메라로 할까요? [y/n]: y
  ✓ camera = 1 (kafka-iphone Camera)

마이크
  [1] kafka-iphone Microphone   (1ch, 48000Hz)
  [3] MacBook Pro Microphone    (1ch, 48000Hz)
  번호: 3
    5초간 말해보세요...
    [████████░░░░░░░░░░░░░░░░]  -21.3 dB
  잘 반응하나요? [y/n]: y
  ✓ audio = 3 (MacBook Pro Microphone)

저장: /Users/alexpereira/Git/detect_objects/.device_config.json
```

- 확인에 실패하거나 `n`을 누르면 **그 장치만 다시 고른다** (처음부터가 아니라).
- 매번 새로 고른다. 저장된 JSON은 캐시가 아니라 **"이번에 뭘 골랐는지" 기록이자
  본 앱(`main.py`)으로 넘기는 통로**다.

## 2. 파일 5개

```
camera_tools/refactored/
├── environment.py   Environment, CaptureBackend   머신 정보 + 백엔드 선택   (의존성 없음)
├── cameras.py       Camera, list_cameras, preview 카메라 목록 + 미리보기    (cv2)
├── audio.py         AudioDevice, list_devices,    마이크 목록 + 레벨 미터   (sounddevice)
│                    level_meter
├── config.py        DeviceConfig                  선택 결과 + JSON 저장/로드 (의존성 없음)
└── setup.py         인터랙티브 마법사 (진입점)
```

```
                setup.py
            ┌──────┼──────┬────────┐
            ▼      ▼      ▼        ▼
       cameras  audio  config  environment
          │       │       │
          ▼       ▼       └──> environment
         cv2  sounddevice
```

원칙:
1. **무거운 라이브러리는 한 파일씩.** cv2는 `cameras.py`만, sounddevice는 `audio.py`만.
   `environment.py`와 `config.py`는 순수 stdlib라 아무 데서나 테스트된다.
2. **떠다니는 dict 금지.** 데이터 묶음은 전부 frozen dataclass.
3. **`setup.py`만 `input()`/`print()`를 쓴다.** 나머지는 라이브러리로 동작한다.

## 3. 저장 파일

`.device_config.json` (프로젝트 루트). **`.gitignore`에 추가할 것** — 인덱스는
머신마다 다르므로 공유하면 안 된다.

```json
{
  "environment": {
    "os": "Darwin", "release": "25.5.0", "machine": "arm64",
    "python": "3.11.14", "rpi": null
  },
  "camera": {
    "index": 1, "name": "kafka-iphone Camera",
    "path": "578340B6-...", "vid": null, "pid": null
  },
  "audio": {
    "index": 3, "name": "MacBook Pro Microphone",
    "channels": 1, "samplerate": 48000.0
  },
  "saved_at": "2026-08-01T22:55:00"
}
```

---

## 4. 파일별 전체 코드

### 4-1. `environment.py`

```python
"""The machine we run on, and the OpenCV backend to list cameras with.

No cv2 import here: backends are stored by *name* ("CAP_AVFOUNDATION"),
and ``cameras`` turns the name into the real constant.
"""

from __future__ import annotations

import json
import platform
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class CaptureBackend:
    """One door OpenCV can use to reach cameras."""

    name: str                       # CLI 이름:         --backend avfoundation
    constant: str                   # OpenCV 상수 이름:  getattr(cv2, ...)
    label: str                      # 리포트에 적는 라벨
    default_for: str | None = None  # 어느 OS의 기본이냐 (아니면 None)


ANY = CaptureBackend("any", "CAP_ANY", "OpenCV automatic")

# 표 하나가 전부. 새 백엔드 추가 = 여기 한 줄.
BACKENDS = (
    ANY,
    CaptureBackend("avfoundation", "CAP_AVFOUNDATION", "AVFoundation", default_for="Darwin"),
    CaptureBackend("msmf", "CAP_MSMF", "Microsoft Media Foundation", default_for="Windows"),
    CaptureBackend("dshow", "CAP_DSHOW", "DirectShow"),  # 윈도우 대안, 기본 아님
    CaptureBackend("v4l2", "CAP_V4L2", "Video4Linux2", default_for="Linux"),
)


@dataclass(frozen=True)
class Environment:
    """Platform details, read once and passed around unchanged."""

    os: str
    release: str
    machine: str
    python: str
    # TODO: 라즈베리파이 모델 감지 — 파이를 연결하면 구현한다.
    #       (/proc/device-tree/model 을 읽으면 됨. 그때까지 어디서든 None.)
    rpi: str | None = None

    @classmethod
    def detect(cls) -> Environment:
        """Read the details from the machine this is running on."""
        return cls(
            # platform.system()이 빈 문자열인 희귀 플랫폼 대비
            os=platform.system() or "Unknown",
            release=platform.release(),
            machine=platform.machine(),
            python=platform.python_version(),
        )

    def capture_backend(self, name: str = "auto") -> CaptureBackend:
        """Return the backend to reach cameras with on this machine.

        ``"auto"`` picks this OS's default; anything else is looked up by name.
        """
        if name == "auto":
            for backend in BACKENDS:
                if backend.default_for == self.os:
                    return backend
            return ANY  # 모르는 OS면 OpenCV한테 맡긴다

        for backend in BACKENDS:
            if backend.name == name:
                return backend

        supported = ", ".join(backend.name for backend in BACKENDS)
        raise ValueError(f"unknown backend {name!r}; expected one of {supported}")

    def as_dict(self) -> dict[str, str | None]:
        """Return a plain dict, because json cannot serialize a dataclass."""
        return asdict(self)

    def __str__(self) -> str:
        """Returns a json-format string for Environment."""
        return json.dumps(self.as_dict(), ensure_ascii=False)


if __name__ == "__main__":
    print(Environment.detect())
```

### 4-2. `cameras.py`

```python
"""List the cameras attached to this machine, and preview one.

The only module that imports cv2.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
from cv2_enumerate_cameras import enumerate_cameras, supported_backends

from camera_tools.refactored.environment import Environment

PREVIEW_WINDOW = "confirm camera - press q"


@dataclass(frozen=True)
class Camera:
    """One camera the operating system reports as attached."""

    index: int              # cv2.VideoCapture(index, backend) 에 넣을 값
    name: str               # "FaceTime HD Camera"
    path: str | None = None # 리눅스면 /dev/video0, 맥이면 uniqueID
    vid: int | None = None  # USB 제조사 ID (리눅스/윈도우에서만)
    pid: int | None = None  # USB 제품 ID


def backend_constant(environment: Environment, backend: str = "auto") -> int:
    """Turn a backend name into the number cv2 wants, or explain why not."""
    chosen = environment.capture_backend(backend)

    if not hasattr(cv2, chosen.constant):
        raise RuntimeError(f"OpenCV does not provide {chosen.constant}.")

    constant = getattr(cv2, chosen.constant)

    # 목록 조회를 지원하는 백엔드는 플랫폼마다 다르다. 조용히 빈 목록을
    # 돌려주면 "카메라 없음"과 구분이 안 되므로 분명하게 알린다.
    if constant not in supported_backends:
        names = ", ".join(
            cv2.videoio_registry.getBackendName(b) for b in supported_backends
        )
        raise RuntimeError(
            f"{chosen.label} cannot list cameras on this platform; try: {names}"
        )

    return constant


def list_cameras(environment: Environment, backend: str = "auto") -> tuple[Camera, ...]:
    """Ask the OS which cameras are attached, without opening any of them."""
    # 백엔드를 넘겨야 raw 인덱스(0, 1, ...)가 나온다. 안 넘기면 backend
    # offset이 더해진 값(1200, 1201, ...)이 나온다.
    return tuple(
        Camera(
            index=info.index,
            name=info.name,
            path=info.path,
            vid=info.vid,
            pid=info.pid,
        )
        for info in enumerate_cameras(backend_constant(environment, backend))
    )


def preview(camera: Camera, constant: int) -> bool:
    """Show a live preview until the user presses q.

    Returns whether any frame actually arrived — a camera can be listed and
    still refuse to open, for example when another app is holding it.
    """
    capture = cv2.VideoCapture(camera.index, constant)

    try:
        if not capture.isOpened():
            return False

        saw_a_frame = False
        while True:
            success, frame = capture.read()
            if not success:
                break

            saw_a_frame = True
            cv2.imshow(PREVIEW_WINDOW, frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        return saw_a_frame
    finally:
        capture.release()
        cv2.destroyAllWindows()
```

### 4-3. `audio.py`

```python
"""List the microphones on this machine, and show a live input level.

The only module that imports sounddevice.
"""

from __future__ import annotations

import math
import time
from dataclasses import asdict, dataclass

import numpy as np
import sounddevice as sd

METER_SAMPLE_RATE = 16000  # Whisper가 쓰는 값과 맞춘다
METER_BLOCK_SIZE = 1024
SILENCE_DB = -60.0  # 이 아래는 무음으로 보고 막대를 비운다


@dataclass(frozen=True)
class AudioDevice:
    """One input device sounddevice reports."""

    index: int
    name: str
    channels: int
    samplerate: float

    def as_dict(self) -> dict:
        return asdict(self)


def list_devices() -> tuple[AudioDevice, ...]:
    """Return every device that can record, in sounddevice index order."""
    return tuple(
        AudioDevice(
            index=index,
            name=info["name"],
            channels=info["max_input_channels"],
            samplerate=float(info["default_samplerate"]),
        )
        for index, info in enumerate(sd.query_devices())
        if info["max_input_channels"] > 0
    )


def _bar(rms: float, width: int = 24) -> str:
    """Draw a level bar from an RMS value."""
    decibels = 20 * math.log10(max(rms, 1e-10))
    # SILENCE_DB(무음) ~ 0 dB(최대) 구간을 막대 길이로 편다.
    ratio = min(max((decibels - SILENCE_DB) / -SILENCE_DB, 0.0), 1.0)
    filled = int(ratio * width)

    return f"[{'█' * filled}{'░' * (width - filled)}] {decibels:6.1f} dB"


def level_meter(device: AudioDevice, seconds: float = 5.0) -> None:
    """Show a live input level for a few seconds so the user can test the mic."""
    level = 0.0

    def record(indata, frames, time_info, status) -> None:
        # 이 콜백은 오디오 스레드에서 돈다. 계산만 하고 출력은 메인에서.
        nonlocal level
        level = float(np.sqrt(np.mean(indata**2)))

    with sd.InputStream(
        device=device.index,
        channels=1,
        samplerate=METER_SAMPLE_RATE,
        blocksize=METER_BLOCK_SIZE,
        callback=record,
    ):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            print(f"\r    {_bar(level)}", end="", flush=True)
            time.sleep(0.05)

    print()  # 막대를 \r로 덮어썼으니 줄을 끝낸다
```

> 왜 콜백에서 바로 안 찍나: 오디오 콜백은 정해진 시간 안에 끝나야 한다.
> `print()`는 느릴 수 있어서, 콜백은 숫자만 저장하고 화면은 메인 루프가 그린다.

### 4-4. `config.py`

```python
"""The devices we settled on, saved as JSON for the app to read."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from camera_tools.refactored.audio import AudioDevice
from camera_tools.refactored.cameras import Camera
from camera_tools.refactored.environment import Environment

# camera_tools/refactored/config.py -> 프로젝트 루트
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / ".device_config.json"


@dataclass(frozen=True)
class DeviceConfig:
    """Everything the app needs to start: which machine, which devices."""

    environment: Environment
    camera: Camera
    audio: AudioDevice
    saved_at: str

    @classmethod
    def create(
        cls, environment: Environment, camera: Camera, audio: AudioDevice
    ) -> DeviceConfig:
        """Stamp the current time and build a config."""
        return cls(
            environment=environment,
            camera=camera,
            audio=audio,
            saved_at=datetime.now().isoformat(timespec="seconds"),
        )

    def as_dict(self) -> dict[str, Any]:
        # asdict()가 중첩된 dataclass까지 재귀로 dict로 바꿔준다.
        return asdict(self)

    def save(self, path: Path = CONFIG_PATH) -> Path:
        """Write the config as JSON and return where it went."""
        path.write_text(str(self) + "\n", encoding="utf-8")
        return path

    @classmethod
    def load(cls, path: Path = CONFIG_PATH) -> DeviceConfig:
        """Read a config back. Raises if the file is missing or malformed."""
        data = json.loads(path.read_text(encoding="utf-8"))

        # dict를 원래 dataclass로 되돌린다. 키가 하나라도 어긋나면
        # TypeError가 나므로, 형식이 깨진 파일을 조용히 넘기지 않는다.
        return cls(
            environment=Environment(**data["environment"]),
            camera=Camera(**data["camera"]),
            audio=AudioDevice(**data["audio"]),
            saved_at=data["saved_at"],
        )

    def __str__(self) -> str:
        """Returns the config as pretty JSON — so print(config) just works."""
        return json.dumps(self.as_dict(), ensure_ascii=False, indent=2)
```

### 4-5. `setup.py` (인터랙티브 마법사)

```python
"""Interactive device setup: pick a camera and a microphone, then save.

The only module that talks to the user.
"""

from __future__ import annotations

import sys
from pathlib import Path

# 이 파일을 스크립트로 직접 실행해도 패키지 import가 되게 한다.
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from camera_tools.refactored import audio, cameras
from camera_tools.refactored.config import DeviceConfig
from camera_tools.refactored.environment import Environment


def ask_index(valid: dict[int, str], prompt: str) -> int:
    """Ask until the user types one of the offered indexes."""
    while True:
        answer = input(prompt).strip()
        if answer.isdigit() and int(answer) in valid:
            return int(answer)

        offered = ", ".join(str(index) for index in valid)
        print(f"  {offered} 중에서 골라주세요.")


def confirm(question: str) -> bool:
    """Ask a yes/no question until the answer is clear."""
    while True:
        answer = input(f"  {question} [y/n]: ").strip().lower()
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False


def choose_camera(environment: Environment) -> cameras.Camera:
    """List cameras, preview the chosen one, and confirm it."""
    found = cameras.list_cameras(environment)
    if not found:
        raise RuntimeError("카메라를 찾지 못했습니다.")

    constant = cameras.backend_constant(environment)
    by_index = {camera.index: camera for camera in found}

    print("\n카메라")
    while True:
        for camera in found:
            print(f"  [{camera.index}] {camera.name}")

        chosen = by_index[ask_index(by_index, "  번호: ")]

        print("    → 미리보기 창이 열립니다. 확인했으면 q를 누르세요.")
        if not cameras.preview(chosen, constant):
            print(f"    ✗ {chosen.name} 에서 영상을 받지 못했습니다. 다시 고르세요.")
            continue

        if confirm("이 카메라로 할까요?"):
            print(f"  ✓ camera = {chosen.index} ({chosen.name})")
            return chosen


def choose_audio() -> audio.AudioDevice:
    """List microphones, run a level meter, and confirm one."""
    found = audio.list_devices()
    if not found:
        raise RuntimeError("마이크를 찾지 못했습니다.")

    by_index = {device.index: device for device in found}

    print("\n마이크")
    while True:
        for device in found:
            print(
                f"  [{device.index}] {device.name}"
                f"   ({device.channels}ch, {device.samplerate:.0f}Hz)"
            )

        chosen = by_index[ask_index(by_index, "  번호: ")]

        print("    5초간 말해보세요...")
        try:
            audio.level_meter(chosen)
        except Exception as error:  # sounddevice가 장치별로 다양한 예외를 던진다
            print(f"    ✗ {chosen.name} 를 열지 못했습니다: {error}")
            continue

        if confirm("잘 반응하나요?"):
            print(f"  ✓ audio = {chosen.index} ({chosen.name})")
            return chosen


def main() -> int:
    """Run the wizard and save the result."""
    environment = Environment.detect()
    print("\n환경")
    print(
        f"  {environment.os} {environment.release} / "
        f"{environment.machine} / Python {environment.python}"
    )

    try:
        config = DeviceConfig.create(
            environment=environment,
            camera=choose_camera(environment),
            audio=choose_audio(),
        )
    except (RuntimeError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
    except (EOFError, KeyboardInterrupt):
        print("\n취소했습니다.", file=sys.stderr)
        return 1

    print(f"\n저장: {config.save()}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
```

> `choose_audio`에서 `except Exception`을 쓴 이유: sounddevice는 장치·드라이버에
> 따라 `PortAudioError`, `ValueError`, `OSError` 등 여러 예외를 던진다. 여기서는
> **잡아서 할 일이 분명하다** — 다시 고르게 하는 것. 이럴 때만 넓게 잡는다.

---

## 5. 테스트

`environment.py`와 `config.py`는 의존성이 없어서 그냥 테스트된다.
`cameras.py`/`audio.py`는 장치 목록 부분만 가짜로 바꿔서 테스트하고,
`preview`/`level_meter`는 실제 하드웨어가 필요하므로 테스트하지 않는다
(사람이 눈·귀로 확인하는 게 그 함수들의 존재 이유다).

### 5-1. `test_environment.py`

```python
"""Tests for platform detection and backend selection. No cv2 needed."""

from __future__ import annotations

import json
import sys
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

from camera_tools.refactored.environment import ANY, BACKENDS, Environment


def env(os_name: str) -> Environment:
    """A fixed environment, so tests never depend on the real machine."""
    return Environment(os=os_name, release="test", machine="arm64", python="3.11")


class EnvironmentTests(unittest.TestCase):
    def test_detect_fills_in_every_field(self) -> None:
        detected = Environment.detect()

        self.assertTrue(detected.os)
        self.assertTrue(detected.python)

    def test_str_is_valid_json_with_every_field(self) -> None:
        decoded = json.loads(str(Environment.detect()))

        self.assertEqual(set(decoded), {"os", "release", "machine", "python", "rpi"})

    def test_the_environment_cannot_be_modified(self) -> None:
        with self.assertRaises(FrozenInstanceError):
            Environment.detect().os = "Windows"


class CaptureBackendTests(unittest.TestCase):
    def test_auto_picks_the_os_default(self) -> None:
        cases = {
            "Darwin": "CAP_AVFOUNDATION",
            "Windows": "CAP_MSMF",
            "Linux": "CAP_V4L2",
        }

        for system, expected in cases.items():
            with self.subTest(system=system):
                self.assertEqual(env(system).capture_backend().constant, expected)

    def test_auto_falls_back_on_an_unknown_os(self) -> None:
        self.assertIs(env("Plan9").capture_backend(), ANY)

    def test_an_explicit_name_ignores_the_os(self) -> None:
        backend = env("Darwin").capture_backend("v4l2")

        self.assertEqual(backend.constant, "CAP_V4L2")
        self.assertEqual(backend.label, "Video4Linux2")

    def test_an_unknown_name_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            env("Linux").capture_backend("directx")

    def test_every_os_default_is_unique(self) -> None:
        # 한 OS에 기본이 둘이면 auto가 앞의 것만 잡는다. 표를 지키는 테스트.
        defaults = [b.default_for for b in BACKENDS if b.default_for]

        self.assertEqual(len(defaults), len(set(defaults)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

### 5-2. `test_config.py`

```python
"""Tests for saving and loading the chosen devices."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

from camera_tools.refactored.audio import AudioDevice
from camera_tools.refactored.cameras import Camera
from camera_tools.refactored.config import DeviceConfig
from camera_tools.refactored.environment import Environment

MAC = Environment(os="Darwin", release="test", machine="arm64", python="3.11")
CAMERA = Camera(index=1, name="kafka-iphone Camera", path="578340B6")
MIC = AudioDevice(index=3, name="MacBook Pro Microphone", channels=1, samplerate=48000.0)


class DeviceConfigTests(unittest.TestCase):
    def config(self) -> DeviceConfig:
        return DeviceConfig.create(environment=MAC, camera=CAMERA, audio=MIC)

    def test_create_stamps_the_time(self) -> None:
        self.assertTrue(self.config().saved_at)

    def test_str_is_json_with_everything_nested(self) -> None:
        decoded = json.loads(str(self.config()))

        self.assertEqual(decoded["camera"]["name"], "kafka-iphone Camera")
        self.assertEqual(decoded["audio"]["index"], 3)
        self.assertEqual(decoded["environment"]["os"], "Darwin")

    def test_a_saved_config_loads_back_identical(self) -> None:
        original = self.config()

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "devices.json"
            original.save(path)

            # @dataclass의 __eq__ 덕분에 필드 단위로 비교된다.
            self.assertEqual(DeviceConfig.load(path), original)

    def test_a_malformed_file_is_not_swallowed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "devices.json"
            path.write_text('{"environment": {}, "camera": {}}', encoding="utf-8")

            with self.assertRaises((KeyError, TypeError)):
                DeviceConfig.load(path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

### 5-3. `test_cameras.py`

```python
"""Tests for the camera list, with enumeration faked."""

from __future__ import annotations

import sys
import unittest
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

from camera_tools.refactored import cameras
from camera_tools.refactored.environment import Environment

MAC = Environment(os="Darwin", release="test", machine="arm64", python="3.11")


@dataclass
class FakeCameraInfo:
    """Stand in for cv2_enumerate_cameras.CameraInfo."""

    index: int
    name: str
    path: str | None = None
    vid: int | None = None
    pid: int | None = None


class ListCamerasTests(unittest.TestCase):
    def list_with(self, infos: list, supported: tuple = (1200,)) -> tuple:
        with (
            patch.object(cameras, "enumerate_cameras", return_value=infos),
            patch.object(cameras, "supported_backends", supported),
        ):
            return cameras.list_cameras(MAC)

    def test_every_listed_camera_is_reported(self) -> None:
        found = self.list_with(
            [FakeCameraInfo(0, "FaceTime HD Camera"), FakeCameraInfo(1, "iPhone")]
        )

        self.assertEqual([c.name for c in found], ["FaceTime HD Camera", "iPhone"])
        self.assertEqual([c.index for c in found], [0, 1])

    def test_no_cameras(self) -> None:
        self.assertEqual(self.list_with([]), ())

    def test_usb_ids_are_carried_through(self) -> None:
        found = self.list_with(
            [FakeCameraInfo(0, "USB Cam", path="/dev/video0", vid=1133, pid=2093)]
        )

        self.assertEqual(found[0].path, "/dev/video0")
        self.assertEqual(found[0].vid, 1133)

    def test_a_backend_that_cannot_list_is_rejected(self) -> None:
        # 맥에서 v4l2를 달라고 하면 조용히 빈 목록이 아니라 에러여야 한다.
        with patch.object(cameras, "supported_backends", (1200,)):
            with self.assertRaises(RuntimeError):
                cameras.backend_constant(MAC, "v4l2")

    def test_an_unknown_backend_name_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            cameras.backend_constant(MAC, "directx")


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

### 5-4. `test_audio.py`

```python
"""Tests for the microphone list and the level bar."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

from camera_tools.refactored import audio

FAKE_DEVICES = [
    {"name": "Speakers", "max_input_channels": 0, "default_samplerate": 48000.0},
    {"name": "MacBook Pro Microphone", "max_input_channels": 1,
     "default_samplerate": 48000.0},
    {"name": "USB Mic", "max_input_channels": 2, "default_samplerate": 44100.0},
]


class ListDevicesTests(unittest.TestCase):
    def test_output_only_devices_are_skipped(self) -> None:
        with patch.object(audio.sd, "query_devices", return_value=FAKE_DEVICES):
            found = audio.list_devices()

        self.assertEqual([d.name for d in found],
                         ["MacBook Pro Microphone", "USB Mic"])

    def test_the_sounddevice_index_is_preserved(self) -> None:
        # 인덱스 0은 출력 전용이라 빠지지만, 남은 것들은 원래 번호를 유지해야
        # 한다. 번호가 밀리면 엉뚱한 장치를 열게 된다.
        with patch.object(audio.sd, "query_devices", return_value=FAKE_DEVICES):
            found = audio.list_devices()

        self.assertEqual([d.index for d in found], [1, 2])


class LevelBarTests(unittest.TestCase):
    def test_silence_draws_an_empty_bar(self) -> None:
        self.assertIn("░" * 24, audio._bar(0.0))

    def test_a_full_signal_fills_the_bar(self) -> None:
        self.assertIn("█" * 24, audio._bar(1.0))

    def test_a_mid_signal_is_partly_filled(self) -> None:
        drawn = audio._bar(0.05)

        self.assertIn("█", drawn)
        self.assertIn("░", drawn)


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

---

## 6. 만드는 순서

```
0. uv add cv2-enumerate-cameras
   .gitignore 에 .device_config.json 추가

1. environment.py  →  uv run python -m unittest camera_tools.refactored.test_environment -v
2. cameras.py      →  ... test_cameras -v
3. audio.py        →  ... test_audio -v
4. config.py       →  ... test_config -v
5. setup.py        →  uv run python -m camera_tools.refactored.setup     ← 직접 해보기
```

`setup.py`는 사람이 직접 돌려봐야 한다 — 창이 뜨는지, 막대가 움직이는지,
`n`을 눌렀을 때 다시 고르게 되는지.

## 7. 다 되면: `main.py` 연결

지금 `main.py`는 마이크만 물어보고 카메라는 `camera_index=1`로 박혀 있다
([main.py:34](../main.py#L34)). 설정 파일을 읽게 바꾼다:

```python
from camera_tools.refactored.config import DeviceConfig

config = DeviceConfig.load()          # 없으면 예외 -> setup 먼저 돌리라고 안내
camera_index = config.camera.index
device_id = config.audio.index
```

그러면 `main.py`에서 장치 고르는 코드가 전부 빠진다.

정리 대상: `camera_tools/find_cameras.py`, `camera_tools/test_find_cameras.py`,
`camera_cv/list_cameras.py` (셋 다 이 모듈로 대체됨), 그리고 디렉터리를
`camera_tools/refactored/` → `devices/` 로 이동.
