import threading
import queue
import traceback
import time

from .camera_cv.camera_cv import Camera_Manager
from .models.factory import create_voice_manager
from .tui.app import run_app
from .voice_text_convert.mic_whisper_manager import Whisper_Audio_Manager
from .voice_text_convert.parse_and_match_module import Text_Manager

class_names_queue: queue.Queue[tuple[list[str], float]] = queue.Queue(maxsize=1)

stop_event = threading.Event()
initialize_barrier = threading.Barrier(
    parties=2,
    action=lambda: print("loading finished"),
)


def put_latest_classes(class_names: list[str]) -> None:
    requested_at = time.perf_counter()
    try:
        class_names_queue.put_nowait((class_names, requested_at))
    except queue.Full:
        try:
            class_names_queue.get_nowait()
        except queue.Empty:
            pass
        class_names_queue.put_nowait((class_names, requested_at))


def detecting_objects(
    supported_classes: list[str],
    camera,
    vision_model_id: str,
):
    try:
        camera_manager = Camera_Manager(
            camera_index=camera.info.index,
            camera_backend=camera.info.backend,
            thread_event=stop_event,
            class_names_queue=class_names_queue,
            supported_classes=supported_classes,
            vision_model_id=vision_model_id,
        )
        camera_manager.load_model()

        print("camera manager setting finished. Waiting for barrier to be ended...\n")
        initialize_barrier.wait()
    except threading.BrokenBarrierError:
        print("barrier wass destructed..\n")
        stop_event.set()
        return
    except Exception as e:
        print(e)
        traceback.print_exc()
        stop_event.set()
        initialize_barrier.abort()
        return
    # camera manager 시작
    try:
        camera_manager.start_record()
    except Exception as e:
        print(e)
        traceback.print_exc()
        stop_event.set()


def voice_text_convert_worker(
    whisper_audio_manager: Whisper_Audio_Manager,
):
    try:
        whisper_audio_manager.load_model()
        whisper_audio_manager.create_stream()
        print("void to text converter is ready. Waiting for other thread..\n")
        initialize_barrier.wait()
    except threading.BrokenBarrierError as e:
        print(e)
        print("barrier was destructed..\n")
        stop_event.set()
        whisper_audio_manager.close()
        return
    except Exception as e:
        print(e)
        stop_event.set()
        initialize_barrier.abort()
        whisper_audio_manager.close()
        return

    try:
        whisper_audio_manager.start()
        print("음성 인식을 시작합니다.")
        print("종료하려면 Ctrl+C를 누르세요.")
        with Text_Manager() as text_manager:
            while not stop_event.is_set():
                text = whisper_audio_manager.get_transcribed_text(timeout=0.5)
                if text is not None:
                    print(f"음성 텍스트 수신: {text}")
                    detected_class_names = text_manager.extract(text)
                    if not detected_class_names:
                        print("일치하는 YOLO 클래스가 없습니다\n")
                        continue
                    put_latest_classes(
                        class_names=[
                            detected_class.yolo_class
                            for detected_class in detected_class_names
                        ]
                    )
                    for class_name in detected_class_names:
                        print(
                            f"한국어={class_name.korean_word}, "
                            f"class_name={class_name.yolo_class}, "
                            f"class_id={class_name.index}"
                        )

    except KeyboardInterrupt as e:
        print(e)
        if not stop_event.is_set():
            print("set stop event\n")
            stop_event.set()
    except Exception as e:
        print(e)
        if not stop_event.is_set():
            print("set stop event\n")
            stop_event.set()
    finally:
        whisper_audio_manager.close()


def main() -> int:
    """Run device setup, voice control, and camera detection."""
    voice_to_text_thread = None

    try:
        context = run_app()
        if context is None:
            return 1

        device_id = context.audio_input.info.index
        with Text_Manager() as text_manager:
            supported_classes = text_manager.get_supported_yolo_classes()

        whisper_audio_manager = create_voice_manager(
            context.models.voice_id,
            device_id=device_id,
        )

        voice_to_text_thread = threading.Thread(
            target=voice_text_convert_worker,
            args=(whisper_audio_manager,),
            name="VoiceTextWorker",
            daemon=True,
        )
        voice_to_text_thread.start()
        detecting_objects(
            supported_classes,
            context.camera,
            context.models.vision_id,
        )
    except KeyboardInterrupt:
        print("종료 요청을 받았습니다.")
    finally:
        stop_event.set()
        if initialize_barrier.n_waiting:
            initialize_barrier.abort()
        if voice_to_text_thread is not None:
            voice_to_text_thread.join(timeout=5.0)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
