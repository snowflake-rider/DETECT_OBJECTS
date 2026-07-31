import numpy as np
import sounddevice as sd
import whisper
import queue
from parse_and_match_module import Text_Manager
import threading

SAMPLE_RATE = 16000
CHANNELS = 1
RECORD_SECONDS = 5
BLOCK_SIZE=1024
MODEL_NAME="base"
MAX_AUDIO_QUEUE_SIZE = 5
MAX_RESULT_QUEUE_SIZE = 5

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
            language='ko',
            dtype="float32"
        ):
        self.__device_id = device_id
        self.__whisper_model:whisper.Whisper = None
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
        self.__audio_queue : queue.Queue[np.ndarray] = queue.Queue(
            maxsize=MAX_AUDIO_QUEUE_SIZE
        )

        self.__result_queue:queue.Queue[str] = queue.Queue(
            maxsize=MAX_RESULT_QUEUE_SIZE
        )
        self.__worker_thread:threading.Thread|None = None
        self.__stop_event = threading.Event()

        self.__is_stream_running = False

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
                    f"요청한 채널 수는 {self.__channels}개이지만, "
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

        if self.__stream.active and self.__is_running:
            self.__stream.stop()
            self.__is_running = False
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
        try:
            self.__audio_queue.put_nowait(
                indata.copy()
            )
        except queue.Full:
            pass

    # 지정된 시간 만큼 데이터를 모으는 메서드
    def collect_audio(self):
        target_samples = int(
            self.__sample_rate * self.__record_seconds
        )
        collected_blocks: list[np.ndarray]=[]
        collected_samples = 0

        while collected_samples < target_samples:
            if self.__stop_event.is_set():
                return None
            try:
                block = self.__audio_queue.get(
                    timeout=0.2
                )
            except queue.Empty:
                continue

            collected_blocks.append(block)
            collected_samples += block.shape[0]

        if not collected_blocks:
            return None

        audio = np.concatenate(
            collected_blocks,
            axis=0,
        )
        audio = audio[:target_samples]
        if audio.shape[1] == 1:
            audio = audio[:,0] 
        return audio.astype(np.float32,copy=False)
    
    # load whisper model
    def load_model(self)->None:
        if self.__whisper_model is not None:
            print("이미 로드되어져 있습니다\n")
            return
        self.__whisper_model = whisper.load_model(name=self.__model_name,device="cpu")

    #transcribe
    def transcribe_audio(
        self,
        audio:np.ndarray,
    )->str:
        if self.__whisper_model is None:
            self.load_model()
        if not isinstance(audio,np.ndarray):
            raise TypeError("audio 는 numpy.ndarray여야 합니다")
        if audio.ndim !=1:
            raise ValueError(
                f"Whisper 입력은 1차원이어야 합니다. "
                f"현재 shape: {audio.shape}"
            )
        audio = audio.astype(
            np.float32,
            copy=False,
        )
        result = self.__whisper_model.transcribe(
            audio=audio,
            language=self.__language,
            task="transcribe",
            fp16=False
        )
        return result["text"].strip()
    # ---------------------------------------
    # --------worker thread-------
    # ---------------------------------------
    def _worker(self)->None:
        print("start Audio worker")
        while not self.__stop_event.is_set():
            try:
                audio = self.collect_audio()
                if audio is None:
                    break
                text = self.transcribe_audio(audio)
                if not text:
                    continue
                self._put_latest_result(text)
            except Exception as error:
                if self.__stop_event.is_set():
                    break
                print(
                    f"Audio worker 오류: {error}"
                )
        print("Audio worker 를 종료했습니다")

    def _put_latest_result(
        self,
        text: str,
    ) -> None:
        try:
            self.__result_queue.put_nowait(text)
        except queue.Full:
            try:
                self.__result_queue.get_nowait()
            except queue.Empty:
                pass
            try:
                self.__result_queue.put_nowait(text)
            except queue.Full:
                pass

    def start_worker(self)-> None:
        if(
            self.__worker_thread is not None
            and self.__worker_thread.is_alive() 
        ):
            return
        self.load_model()
        self.__stop_event.clear()
        self.__worker_thread = threading.Thread(
            target=self._worker,
            name="WhisperAudioWorker",
            daemon=False
        )
        self.__worker_thread.start()

    def stop_worker(self)->None:
        self.__stop_event.set()
        if (
            self.__worker_thread is not None
            and self.__worker_thread.is_alive()
        ):
            self.__worker_thread.join(
                timeout=3.0
            )
        self.__worker_thread = None

    # --------------------------------------------------
    # Main thread에서 결과 가져오기
    # --------------------------------------------------

    def get_transcribed_text(
        self,
        timeout: float | None = None,
    ) -> str | None:
        try:
            return self.__result_queue.get(
                timeout=timeout
            )

        except queue.Empty:
            return None

    # --------------------------------------------------
    # 통합 시작/종료
    # --------------------------------------------------
    @staticmethod
    def _clear_queue(
        target_queue: queue.Queue,
    ) -> None:
        while True:
            try:
                target_queue.get_nowait()
            except queue.Empty:
                break

    def start(self)->None:
        self.start_stream()
        self.start_worker()

    def close(self)->None:
        self.stop_worker()
        self.stop_stream()
        self.close_stream()
        self._clear_queue(
            self.__audio_queue
        )
        self._clear_queue(
            self.__result_queue
        )

def main() -> None:
    manager: Whisper_Audio_Manager | None = None

    try:
        devices = (
            Whisper_Audio_Manager
            .get_input_devices()
        )

        for device in devices:
            print(device)

        device_id = int(
            input("마이크 device id를 입력하세요: ")
        )

        manager = Whisper_Audio_Manager(
            device_id=device_id,
            model_name="base",
            sample_rate=16000,
            channels=1,
            block_size=1024,
            record_seconds=5,
            language="ko",
        )

        manager.start()

        print("음성 인식을 시작합니다.")
        print("종료하려면 Ctrl+C를 누르세요.")
        with Text_Manager() as text_manager:
            while True:
                text = manager.get_transcribed_text(
                    timeout=0.5
                )

                if text is not None:
                    print("\n========== 음성 인식 결과 ==========")
                    print(f"텍스트: {text}")

                    detected_classes = text_manager.extract(text)
                    if not detected_classes:
                        print("YOLO 클래스: 일치하는 클래스가 없습니다.")
                        continue

                    print("========== YOLO 클래스 ==========")
                    for detected in detected_classes:
                        print(
                            f"한국어={detected.korean_word}, "
                            f"class_name={detected.yolo_class}, "
                            f"class_id={detected.index}"
                        )

    except KeyboardInterrupt:
        print("\n사용자가 프로그램을 종료했습니다.")

    except Exception as error:
        print(f"오류 발생: {error}")

    finally:
        if manager is not None:
            manager.close()


if __name__ == "__main__":
    main()
