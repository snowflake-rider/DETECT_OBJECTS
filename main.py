import threading
import queue
import traceback
import numpy as np

from camera_cv.camera import Camera_Manager
from models.yolo_world_module import YOLO_World_Manager
from voice_text_convert.mic_whisper_manager import Whisper_Audio_Manager
from voice_text_convert.parse_and_match_module import Text_Manager

class_names_queue: queue.Queue[list[str]] = queue.Queue(maxsize=1)
ready_model_queue: queue.Queue[
    tuple[YOLO_World_Manager, list[str]]
] = queue.Queue(maxsize=1)

stop_event = threading.Event()
initialize_barrier = threading.Barrier(
    parties=2,
    action=lambda: print("loading finished"),
)

def put_latest_classes(class_names:list[str])->None:
    try:
        class_names_queue.put_nowait(class_names)
    except queue.Full:
        try:
            class_names_queue.get_nowait()
        except queue.Empty:
            pass
        class_names_queue.put_nowait(class_names)


def model_builder_worker() -> None:
    """Build and warm a replacement model without touching the active model."""
    while not stop_event.is_set():
        try:
            classes = class_names_queue.get(timeout=0.5)
        except queue.Empty:
            continue

        # If several commands arrived, build only the newest class set.
        while True:
            try:
                classes = class_names_queue.get_nowait()
            except queue.Empty:
                break

        new_manager = None
        try:
            print(f"새 YOLO 모델 준비 시작: {classes}")
            new_manager = YOLO_World_Manager(confidence=0.65)
            new_manager.load()
            new_manager.set_classes(classes)

            dummy_frame = np.zeros((640, 640, 3), dtype=np.uint8)
            new_manager.predict(dummy_frame)

            # Do not publish a stale model if a newer voice command arrived
            # while this model was being prepared.
            if not class_names_queue.empty():
                print(f"더 최신 요청이 있어 준비한 모델을 폐기합니다: {classes}")
                new_manager.close()
                new_manager = None
                continue

            try:
                ready_model_queue.put_nowait((new_manager, classes))
            except queue.Full:
                old_ready_manager, _ = ready_model_queue.get_nowait()
                old_ready_manager.close()
                ready_model_queue.put_nowait((new_manager, classes))

            print(
                f"새 YOLO 모델 준비 완료: classes={classes}, "
                f"device={new_manager.device}"
            )
            new_manager = None
        except Exception as error:
            print(f"새 YOLO 모델 준비 실패: {error}")
            traceback.print_exc()
        finally:
            if new_manager is not None:
                new_manager.close()

def detecting_objects():
    try:
        camera_manager = Camera_Manager(
            camera_index=1,
            thread_event=stop_event,
            ready_model_queue=ready_model_queue,
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
                text = whisper_audio_manager.get_transcribed_text(
                    timeout=0.5
                ) 
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

if __name__ == "__main__":
    voice_to_text_thread = None
    model_builder_thread = None

    try:
        # 터미널 입력은 다른 스레드와 카메라를 시작하기 전에 완료한다.
        devices = Whisper_Audio_Manager.get_input_devices()
        for device in devices:
            print(device)

        device_id = int(input("마이크 device id를 입력하세요: "))
        whisper_audio_manager = Whisper_Audio_Manager(
            device_id=device_id,
            model_name="base",
            sample_rate=16000,
            channels=1,
            block_size=1024,
            record_seconds=5,
            language="ko",
        )

        voice_to_text_thread = threading.Thread(
            target=voice_text_convert_worker,
            args=(whisper_audio_manager,),
            name="VoiceTextWorker",
            daemon=True,
        )
        model_builder_thread = threading.Thread(
            target=model_builder_worker,
            name="YoloModelBuilder",
            daemon=True,
        )
        model_builder_thread.start()
        voice_to_text_thread.start()
        detecting_objects()
    except KeyboardInterrupt:
        print("종료 요청을 받았습니다.")
    finally:
        stop_event.set()
        if initialize_barrier.n_waiting:
            initialize_barrier.abort()
        if voice_to_text_thread is not None:
            voice_to_text_thread.join(timeout=5.0)
        if model_builder_thread is not None:
            model_builder_thread.join(timeout=5.0)

        while True:
            try:
                unused_manager, _ = ready_model_queue.get_nowait()
                unused_manager.close()
            except queue.Empty:
                break
   
