import numpy as np
import sounddevice as sd
import whisper
import torch
import math

SAMPLE_RATE = 16_000
CHANNELS = 1
RECORD_SECONDS = 5
BLOCK_SIZE=1024
MODEL_NAME="base"

class Whisper_Audio_Manager:
    #| 설정               | 의미               |
    #| ---------------- | ---------------- |
    #| `model_name`     | Whisper 모델 이름    |
    # | `device_id`      | 사용할 마이크 장치 번호    |
    # | `sample_rate`    | 초당 수집할 오디오 샘플 개수 |
    # | `channels`       | 입력 오디오 채널 수      |
    # | `dtype`          | 오디오 샘플 자료형       |
    # | `block_size`     | 콜백 한 번에 받을 샘플 수  |
    # | `record_seconds` | 한 번 인식할 음성 길이    |
    # | `language`       | Whisper가 인식할 언어  |

    def __init__(
            self,
            device_id,
            model_name=MODEL_NAME,
            sample_rate=SAMPLE_RATE,
            channels=CHANNELS,
            record_seconds=RECORD_SECONDS,
            is_use_stream=False,
            block_size=BLOCK_SIZE,
            language='kr',
            dtype="float32"
        ):
        self.__device_id = device_id
        self.__whisper_model = None
        self.__model_name = model_name
        self.__sample_rate = sample_rate
        self.__channels = channels
        self.__record_seconds = record_seconds
        self.__is_use_stream = is_use_stream
        self.__block_size = block_size
        self.__language = language
        self.__dtype = dtype

        self.__stream:sd.InputStream | None = None
        self.__is_running = False

    # 장치 목록 출력
    @staticmethod
    def get_input_devices()->list[dict]:
        devices = sd.query_devices()

        input_devices:list[dict]=[]

        for device_id,device_info in enumerate(devices):
            if device_info["max_input_channels"] > 0:
                input_devices.append(
                    {
                        "id": device_id,
                        "name": device_info["name"],
                        "hostapi": device_info["hostapi"],
                        "max_input_channels": device_info[
                            "max_input_channels"
                        ],
                        "default_samplerate": device_info[
                            "default_samplerate"
                        ],
                        "default_low_input_latency": device_info[
                            "default_low_input_latency"
                        ],
                        "default_high_input_latency": device_info[
                            "default_high_input_latency"
                        ],
                    }
                )
        return input_devices

    # device 에서 default 로 설정된 mic
    @staticmethod
    def get_default_input_device_id()->int:
        default_device = sd.default.device
        default_input_device_id = default_device[0]

        if default_input_device_id is None:
            raise RuntimeError("No default device was setted")

        default_input_device_id = int(default_input_device_id)
        if default_input_device_id <0 :
            raise RuntimeError("No available input device")
        return default_input_device_id
    # mic 장치 점검
    def validate_input_device(self,device_id:int)->None:
        try:
            device_info = sd.query_devices(
                device=device_id,
                kind="input"
            )
            if self.__channels>device_info["max_input_channels"]:
                raise ValueError(
                    f"요청한 채널 수는 {self._channels}개이지만, "
                    f"장치가 지원하는 최대 입력 채널 수는 "
                    f"{device_info['max_input_channels']}개입니다."
                )
            sd.check_input_settings(
                device=device_id,
                samplerate=self.__sample_rate,
                channels=self.__channels,
                dtype=self.__dtype
            )
            print("finished validation!\n")
        except sd.PortAudioError as error:
            raise RuntimeError(f"입력 장치 설정을 사용할 수 없습니다: {error}") from error
    @staticmethod
    def get_input_device_info(device_id: int) -> dict:
        try:
            device_info = sd.query_devices(
                device=device_id,
                kind="input",
            )
        except (sd.PortAudioError, ValueError) as error:
            raise ValueError(
                f"입력 장치 {device_id}를 찾을 수 없습니다."
            ) from error

        return dict(device_info)
    # 선택한 mic 장비 상세 정보 설정해주는 method    
    def select_input_device(
        self
    ) -> dict:
        if self.__device_id is None:
            self.__device_id = self.get_default_input_device_id()
        self.validate_input_device(self.__device_id)
        device_info = self.get_input_device_info(self.__device_id)
        self.__device_id = self.__device_id
        return device_info

    # create stream
    def create_stream(self)->None:
        if self.__device_id is None:
            raise RuntimeError("입력 장치가 선택되지 않았습니다")
        if self.__stream is not None:
            raise RuntimeError("입력 스트림이 이미 생성되어 있습니다")
        self.validate_input_device(self.__device_id)
        self.__stream = sd.InputStream(
            device=self.__device_id,
            samplerate=self.__sample_rate,
            channels=self.__channels,
            dtype=self.__dtype,
            blocksize=self.__block_size,
            callback=self._audio_callback
        )

    # start stream
    def start_stream(self)->None:
        if self.__stream is None:
            self.create_stream()
        if self.__stream.active:
            return
        self.__stream.start()
        self.__is_running = True
        print("마이크 입력 스트림을 시작했습니다")

    def stop_stream(self) -> None:
        if self.__stream is  None:
            return

        if self.__stream.active:
            self.__stream.stop()
        self._is_running = False
        print("마이크 입력 스트림을 중지했습니다.")

    def close_stream(self) -> None:
        if self.__stream is None:
            return

        if self.__stream.active:
            self.__stream.stop()

        self.__stream.close()
        self.__stream = None
        self.__is_running = False

        print("마이크 입력 스트림을 닫았습니다.")



    # Audio Input Stream
    import numpy as np

    # stream callback
    # indata : 각 체널의 frame data (np array) 오디오 signal 의 진폭값을 나타냄

    def _audio_callback(
        self,
        indata: np.ndarray,
        frames: int,
        time_info,
        status: sd.CallbackFlags,
    ) -> None:
        if status:
            print(f"\n오디오 상태: {status}")
        print(f"indata : {indata}\n")
        print(f"frames : {frames}\n")
        # rms = 평균적인 음량자
        rms = float(
            np.sqrt(np.mean(np.square(indata)))
        )

        print(
            f"\rframes={frames}, "
            f"shape={indata.shape}, "
            f"RMS={rms:.6f}",
            end="",
        )
    

if __name__=="__main__":
    devices = Whisper_Audio_Manager.get_input_devices()
    for device in devices:
        print(f"{device}\n")
    try:
        default_device = Whisper_Audio_Manager.get_default_input_device_id()
        device_id = int(input("device id 를 입력하세요\n"))
        manager = Whisper_Audio_Manager(device_id=device_id)
        info=manager.select_input_device()
        print(info)
        manager.create_stream()
        manager.start_stream()
        while True:
                pass

    except Exception as e:
        print(e)
    except KeyboardInterrupt as e:
        print("keyboard interrupt occurred!\n")
    finally:
        manager.stop_stream()