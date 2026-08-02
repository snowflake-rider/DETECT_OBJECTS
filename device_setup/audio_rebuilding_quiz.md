# Audio Rebuilding Quiz

이 문제 은행은 audio.py를 그대로 외우는 대신, 구조와 설계 결정을 이해하고
audio_rebuilding.py를 직접 완성하기 위한 학습 자료입니다.

- 원본: [audio.py](./audio.py)
- 학습용 뼈대 이름: audio_rebuilding.py (필요할 때 별도로 생성)
- 전체 문제: 20
- 한 라운드: 5문제
- 현재 진행률: 0/20

## 학습 규칙

1. 먼저 원본 audio.py를 닫고 문제를 풉니다.
2. Python, sounddevice, Rich 공식 문서는 참고해도 됩니다.
3. 원본 구현을 복사하지 않습니다.
4. 답은 문제 ID와 함께 채팅에 제출합니다.
5. 틀린 개념은 이후 라운드에서 다른 형태로 다시 출제합니다.
6. 정답은 이 파일에 포함하지 않습니다.

## Coverage Matrix

| 범위 | 관련 문제 | 확인할 능력 |
|---|---|---|
| 전체 architecture | AUDIO-01, AUDIO-10, AUDIO-19 | 실행 흐름과 책임 경계 설명 |
| data model과 상태 | AUDIO-02, AUDIO-03, AUDIO-04 | 정보 객체와 runtime 객체 구분 |
| 장치 검색 | AUDIO-05, AUDIO-06, AUDIO-17 | 외부 장치 데이터를 안전하게 변환 |
| 선택 interface | AUDIO-07, AUDIO-08, AUDIO-09 | table, 입력 검증, method 유형 |
| Sound Level 계산 | AUDIO-11, AUDIO-12 | RMS, dB, 범위 제한 |
| callback과 resource | AUDIO-13, AUDIO-14, AUDIO-15, AUDIO-16 | thread 경계, cleanup, 오류 처리 |
| 재구현과 변경 | AUDIO-18, AUDIO-19, AUDIO-20 | 테스트, 설계 변경, closed-book 구현 |

## Progress

- [ ] Round 1 — 구조, data model, 장치 검색
- [ ] Round 2 — 선택 interface와 control flow
- [ ] Round 3 — Sound Level, callback, resource lifetime
- [ ] Round 4 — 테스트, 설계 변경, closed-book 재구현

---

## Round 1 — 구조, Data Model, 장치 검색

### - [ ] AUDIO-01 [architecture]

Audio.setup()이 시작된 후 최종적으로 Audio 또는 None을 반환하기까지 가능한
실행 경로를 순서도로 설명하세요.

> 내 답:

### - [ ] AUDIO-02 [responsibility]

AudioInfo와 Audio를 하나의 클래스로 합치지 않고 분리한 이유는 무엇인가요?
각 클래스가 소유해야 하는 책임을 구분해서 설명하세요.

> 내 답:

### - [ ] AUDIO-03 [immutability]

AudioInfo의 dataclass에 frozen=True가 설정되어 있습니다. 이것이 어떤 동작을
만들고, 선택된 장치 정보에 왜 유용한지 설명하세요.

> 내 답:

### - [ ] AUDIO-04 [state-lifecycle]

Audio.__init__()은 AudioInfo만 저장하고 microphone stream을 열지 않습니다.
장치 I/O를 생성자에서 시작하지 않는 것이 왜 좋은 설계인지 설명하세요.

> 내 답:

### - [ ] AUDIO-05 [device-index]

list_devices()가 출력 전용 장치를 제거한 뒤 새로운 순번을 장치 index로 사용하면
어떤 문제가 생길 수 있나요? 원래 query_devices()의 index를 보존해야 하는
이유를 설명하세요.

> 내 답:

---

## Round 2 — 선택 Interface와 Control Flow

### - [ ] AUDIO-06 [filtering]

max_input_channels가 0인 장치를 마이크 목록에서 제외해야 하는 이유는 무엇인가요?
이 조건을 빠뜨렸을 때 사용자가 경험할 수 있는 실패를 예측하세요.

> 내 답:

### - [ ] AUDIO-07 [default-device]

운영체제의 기본 입력 장치를 table에 표시하려면 어떤 정보 두 개를 비교해야
할까요? 기본 장치가 없거나 유효하지 않을 가능성도 함께 고려하세요.

> 내 답:

### - [ ] AUDIO-08 [index-mapping]

사용자에게 보여주는 선택 번호는 1부터 시작하지만 Python list position은 0부터
시작합니다. 이 차이를 잘못 처리했을 때 발생할 수 있는 경계 오류 두 가지를
설명하세요.

> 내 답:

### - [ ] AUDIO-09 [method-types]

list_devices()는 staticmethod이고 choose()는 classmethod이며 test()는 instance
method입니다. 각 method 유형이 해당 책임과 어떻게 연결되는지 설명하세요.

> 내 답:

### - [ ] AUDIO-10 [setup-control-flow]

다음 네 상황에서 setup()이 무엇을 반환해야 하는지 표로 작성하세요.

1. 사용자가 장치 선택을 취소함
2. 장치를 선택하고 테스트는 거절함
3. 장치를 선택하고 테스트에 성공함
4. 장치를 선택했지만 테스트에 실패함

각 반환 결정이 선택 상태를 어떻게 보호하는지도 설명하세요.

> 내 답:

---

## Round 3 — Sound Level, Callback, Resource Lifetime

### - [ ] AUDIO-11 [signal-math]

RMS 값을 그대로 보여주지 않고 dB로 변환하는 이유는 무엇인가요? RMS가 0일 때
logarithm 계산에서 발생할 수 있는 문제와 필요한 방어 조건을 설명하세요.

> 내 답:

### - [ ] AUDIO-12 [invariant]

_level_bar(rms, width)가 어떤 입력을 받더라도 지켜야 하는 invariant를 세 가지
작성하세요. 조용한 입력, 큰 입력, width 경계를 포함하세요.

> 내 답:

### - [ ] AUDIO-13 [closure]

test() 내부의 record() callback이 바깥 함수의 rms와 received_audio를 변경하려면
어떤 Python 개념이 필요한가요? 해당 선언이 없으면 어떤 문제가 생기는지도
설명하세요.

> 내 답:

### - [ ] AUDIO-14 [thread-boundary]

audio callback 안에서는 RMS 계산과 상태 갱신만 하고 Rich rendering은 main
loop에서 수행합니다. callback 안에서 print, sleep, 화면 갱신을 하면 안 되는
이유를 설명하세요.

> 내 답:

### - [ ] AUDIO-15 [resource-lifetime]

Sound Level 테스트 도중 Ctrl+C가 발생하는 경우를 추적하세요. KeyboardInterrupt가
처리되는 위치와 InputStream 및 Rich Live가 정리되는 순서를 설명하세요.

> 내 답:

---

## Round 4 — 오류, 테스트, 설계 변경, 재구현

### - [ ] AUDIO-16 [error-handling]

microphone을 열 수 없어 PortAudioError가 발생했습니다. 사용자 메시지, resource
정리, test()의 반환값이 각각 어떻게 처리되어야 하는지 설명하세요.

> 내 답:

### - [ ] AUDIO-17 [testing]

실제 microphone 없이 list_devices()를 테스트한다고 가정하세요. 무엇을 fake 또는
mock해야 하며, 최소한 어떤 세 가지 사례를 검증해야 하나요?

> 내 답:

### - [ ] AUDIO-18 [debugging]

다음과 같은 잘못된 구현이 있다고 가정하세요.

    for index, device in enumerate(sd.query_devices()):
        microphones.append(AudioInfo(...))

이 코드는 어떤 장치를 잘못 포함할 수 있나요? 실패를 드러내는 작은 test fixture를
설계하세요.

> 내 답:

### - [ ] AUDIO-19 [transfer]

Ctrl+C 대신 사용자가 q를 입력하거나 10초가 지나면 테스트가 끝나도록 요구사항이
변경되었습니다. 어떤 component의 책임과 resource lifetime이 달라져야 하는지
설명하세요. 아직 구현 코드는 작성하지 마세요.

> 내 답:

### - [ ] AUDIO-20 [closed-book-reconstruction]

원본을 닫고 audio_rebuilding.py의 list_devices()를 직접 구현하세요. 구현 후
다음을 설명하세요.

1. 입력 장치 판별 조건
2. 원본 index를 보존하는 방법
3. 외부 device 데이터를 AudioInfo로 변환하는 경계
4. 장치가 없을 때의 반환값

> 내 답 또는 구현 위치:

---

## Learning Ledger

- Target: audio.py 재구현
- Current component: Round 1 / architecture
- Concepts demonstrated:
- Concepts still uncertain:
- Current hint level: 1 — diagnostic question
- Quiz progress: 0/20
- Weak quiz tags:
- Evidence completed:
- Next exercise: Round 1의 AUDIO-01부터 AUDIO-05까지 답하기
