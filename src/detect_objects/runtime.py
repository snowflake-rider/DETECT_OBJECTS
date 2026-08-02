"""Prepare and run ODIA after the user finishes device setup."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import queue
import threading
import time
import traceback

from .camera_cv.camera_cv import Camera_Manager
from .device_setup import Context
from .models.factory import create_voice_manager
from .voice_text_convert.mic_whisper_manager import Whisper_Audio_Manager
from .voice_text_convert.parse_and_match_module import Text_Manager


@dataclass(frozen=True)
class StartupUpdate:
    """One short progress update shown on the startup screen."""

    step: str
    message: str
    finished: bool = False


StartupReporter = Callable[[StartupUpdate], None]

STARTUP_STEPS = (
    "classes",
    "voice",
    "microphone",
    "camera",
    "vision",
)


class LocalRuntime:
    """Own the models, queues, threads, and cleanup for one local run."""

    def __init__(self, context: Context) -> None:
        self.context = context
        self.class_names_queue: queue.Queue[tuple[list[str], float]] = queue.Queue(
            maxsize=1
        )
        self.shutdown_event = threading.Event()
        self.camera_manager: Camera_Manager | None = None
        self.whisper_manager: Whisper_Audio_Manager | None = None
        self.voice_thread: threading.Thread | None = None
        self._prepared = False
        self._closed = False
        self._lifecycle_lock = threading.RLock()

    def prepare(self, report: StartupReporter) -> None:
        """Load everything needed before opening the live camera window."""
        with self._lifecycle_lock:
            try:
                report(StartupUpdate("classes", "Validating class names…"))
                with Text_Manager() as text_manager:
                    supported_classes = text_manager.get_supported_yolo_classes()
                report(
                    StartupUpdate(
                        "classes",
                        f"Class names ready — {len(supported_classes)} classes",
                        finished=True,
                    )
                )

                report(StartupUpdate("voice", "Loading voice model…"))
                self.whisper_manager = create_voice_manager(
                    self.context.models.voice_id,
                    device_id=self.context.audio_input.info.index,
                )
                self.whisper_manager.load_model()
                report(StartupUpdate("voice", "Voice model ready", finished=True))

                microphone_name = self.context.audio_input.info.name
                report(StartupUpdate("microphone", f"Opening {microphone_name}…"))
                self.whisper_manager.create_stream()
                report(
                    StartupUpdate(
                        "microphone",
                        f"Microphone ready — {microphone_name}",
                        finished=True,
                    )
                )

                camera_name = self.context.camera.info.name
                report(StartupUpdate("camera", f"Preparing {camera_name}…"))
                self.camera_manager = Camera_Manager(
                    camera_index=self.context.camera.info.index,
                    camera_backend=self.context.camera.info.backend,
                    thread_event=self.shutdown_event,
                    class_names_queue=self.class_names_queue,
                    supported_classes=supported_classes,
                    vision_model_id=self.context.models.vision_id,
                )
                report(
                    StartupUpdate(
                        "camera",
                        f"Camera ready — {camera_name}",
                        finished=True,
                    )
                )

                report(StartupUpdate("vision", "Loading vision model…"))
                self.camera_manager.load_model()
                report(
                    StartupUpdate(
                        "vision",
                        "Vision model ready — "
                        f"{self.camera_manager.inference_device_name}",
                        finished=True,
                    )
                )
                self._prepared = True
            except Exception:
                self.close()
                raise

    def run(self) -> None:
        """Start voice recognition, then run camera detection on this thread."""
        if not self._prepared:
            raise RuntimeError("ODIA must finish startup before it can run.")
        if self.camera_manager is None or self.whisper_manager is None:
            raise RuntimeError("ODIA startup did not create its managers.")

        self.voice_thread = threading.Thread(
            target=self._run_voice,
            name="VoiceTextWorker",
            daemon=True,
        )
        self.voice_thread.start()

        try:
            self.camera_manager.start_record()
        except Exception as error:
            print(error)
            traceback.print_exc()
            self.shutdown_event.set()
        finally:
            self.close()

    def _put_latest_classes(self, class_names: list[str]) -> None:
        """Keep only the newest voice request for the camera loop."""
        requested_at = time.perf_counter()
        try:
            self.class_names_queue.put_nowait((class_names, requested_at))
        except queue.Full:
            try:
                self.class_names_queue.get_nowait()
            except queue.Empty:
                # Another thread removed the old request first. That is okay.
                pass
            self.class_names_queue.put_nowait((class_names, requested_at))

    def _run_voice(self) -> None:
        """Read Whisper results and send matching classes to the camera."""
        if self.whisper_manager is None:
            return

        try:
            self.whisper_manager.start()
            print("음성 인식을 시작합니다.")
            print("종료하려면 Ctrl+C를 누르세요.")

            with Text_Manager() as text_manager:
                while not self.shutdown_event.is_set():
                    text = self.whisper_manager.get_transcribed_text(timeout=0.5)
                    if text is None:
                        continue

                    print(f"음성 텍스트 수신: {text}")
                    detected_classes = text_manager.extract(text)
                    if not detected_classes:
                        print("일치하는 YOLO 클래스가 없습니다\n")
                        continue

                    self._put_latest_classes(
                        [detected.yolo_class for detected in detected_classes]
                    )
                    for detected in detected_classes:
                        print(
                            f"한국어={detected.korean_word}, "
                            f"class_name={detected.yolo_class}, "
                            f"class_id={detected.index}"
                        )
        except Exception as error:
            print(error)
            traceback.print_exc()
            self.shutdown_event.set()
        finally:
            self.whisper_manager.close()

    def close(self) -> None:
        """Stop active work and release any resources that were created."""
        with self._lifecycle_lock:
            if self._closed:
                return
            self._closed = True
            self.shutdown_event.set()

            if self.voice_thread is not None and self.voice_thread.is_alive():
                self.voice_thread.join(timeout=5.0)
            elif self.whisper_manager is not None:
                self.whisper_manager.close()

            if self.camera_manager is not None:
                self.camera_manager.unload()
