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

    # Which startup row should change, such as "classes" or "voice".
    step: str

    # The text shown to the user.
    message: str

    # False means working; True means this step is complete.
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
        # __init__ runs automatically when main.py calls LocalRuntime(context).
        # self is the new LocalRuntime object being created.

        # Keep the devices, models, theme, and mode selected in the TUI.
        self.context = context

        # This queue is a thread-safe mailbox from Whisper to the camera.
        # One item looks like: (["person", "bottle"], request_time).
        # maxsize=1 means it keeps space for only one voice request.
        self.class_names_queue: queue.Queue[tuple[list[str], float]] = queue.Queue(
            maxsize=1
        )

        # ⭐ shutdown_event is a shared, thread-safe stop signal.
        # Its type is threading.Event, a thread synchronization tool.
        # It is safer than using a plain shared True/False variable.
        #
        # This is not a mutex:
        # - A mutex lets only one thread use protected code at a time.
        # - An Event shares a signal that many threads can check.
        #
        # Both threads share this exact same Event object:
        #
        #                    shared shutdown_event
        #                       False -> True
        #                            ^
        #                            |
        #                 either side can set it
        #                       +----+----+
        #                       |         |
        #                  Voice loop  Camera loop
        #                   checks it   checks it
        #
        # .set() changes the signal to True. It does not stop a thread itself.
        # Each loop calls .is_set(), notices True, and then stops itself.
        self.shutdown_event = threading.Event()

        # These objects do not exist yet. prepare() creates them later.
        self.camera_manager: Camera_Manager | None = None
        self.whisper_manager: Whisper_Audio_Manager | None = None

        # The voice thread is also created later in run().
        self.voice_thread: threading.Thread | None = None

        # prepare() changes this to True when startup is complete.
        self._prepared = False

        # close() changes this to True so cleanup happens only once.
        self._closed = False

        # This lock prevents prepare() and close() from changing resources together.
        self._lifecycle_lock = threading.RLock()

    def prepare(self, report: StartupReporter) -> None:
        """Load everything needed before opening the live camera window."""
        # report is a function given by the startup TUI.
        # Calling it sends a progress message to the startup screen.

        # Only prepare() or close() may change the resources at one time.
        with self._lifecycle_lock:
            # If any startup step fails, the except block below cleans up.
            try:
                # Tell the TUI which step is starting.
                report(StartupUpdate("classes", "Validating class names…"))

                # Text_Manager reads and checks the supported object names.
                # with closes Text_Manager automatically after this block.
                with Text_Manager() as text_manager:
                    supported_classes = text_manager.get_supported_yolo_classes()

                # Keep the checked list for the camera manager created below.
                # Tell the TUI that this step is finished.
                report(
                    StartupUpdate(
                        "classes",
                        f"Class names ready — {len(supported_classes)} classes",
                        finished=True,
                    )
                )

                # Tell the TUI that voice-model loading is starting.
                report(StartupUpdate("voice", "Loading voice model…"))

                # Read the selected voice model and microphone from context.
                # create_voice_manager() creates the correct manager for that model.
                # Store it on self so run() and close() can use it later.
                self.whisper_manager = create_voice_manager(
                    self.context.models.voice_id,
                    device_id=self.context.audio_input.info.index,
                )

                # Now load the actual voice model into memory.
                self.whisper_manager.load_model()

                # Tell the TUI that voice-model loading is complete.
                report(StartupUpdate("voice", "Voice model ready", finished=True))

                # Get the selected microphone's readable name for the TUI.
                microphone_name = self.context.audio_input.info.name
                report(StartupUpdate("microphone", f"Opening {microphone_name}…"))

                # Create the path that will carry microphone audio into ODIA.
                # This prepares the stream; voice work starts it later in run().
                self.whisper_manager.create_stream()

                # Tell the TUI that the microphone is ready.
                report(
                    StartupUpdate(
                        "microphone",
                        f"Microphone ready — {microphone_name}",
                        finished=True,
                    )
                )

                # Get the selected camera's readable name for the TUI.
                camera_name = self.context.camera.info.name
                report(StartupUpdate("camera", f"Preparing {camera_name}…"))

                # Create the object that will manage the camera and YOLO.
                # This does not start the camera or load YOLO yet.
                self.camera_manager = Camera_Manager(
                    # Which camera the user selected.
                    camera_index=self.context.camera.info.index,
                    # How OpenCV should communicate with that camera.
                    camera_backend=self.context.camera.info.backend,
                    # The shared signal that tells camera work to stop.
                    thread_event=self.shutdown_event,
                    # The mailbox that receives object names from Whisper.
                    class_names_queue=self.class_names_queue,
                    # Every object name that ODIA allows.
                    supported_classes=supported_classes,
                    # Which YOLO model the user selected.
                    vision_model_id=self.context.models.vision_id,
                )

                # Tell the TUI that the camera manager is ready.
                report(
                    StartupUpdate(
                        "camera",
                        f"Camera ready — {camera_name}",
                        finished=True,
                    )
                )

                # Tell the TUI that YOLO loading is starting.
                report(StartupUpdate("vision", "Loading vision model…"))

                # Load the selected YOLO model into memory.
                self.camera_manager.load_model()

                # Show which device will run YOLO, such as CPU, CUDA, or MPS.
                report(
                    StartupUpdate(
                        "vision",
                        "Vision model ready — "
                        f"{self.camera_manager.inference_device_name}",
                        finished=True,
                    )
                )

                # run() is now allowed to start voice and camera processing.
                self._prepared = True

            # If any preparation step fails, release everything created so far.
            # Then raise the same error again so the startup TUI can show it.
            except Exception:
                self.close()
                raise

    def run(self) -> None:
        """Start voice recognition, then run camera detection on this thread."""
        # Do not run if prepare() did not finish successfully.
        if not self._prepared:
            raise RuntimeError("ODIA must finish startup before it can run.")

        # Both managers should exist after prepare().
        # "or" means this error happens if either one is missing.
        if self.camera_manager is None or self.whisper_manager is None:
            raise RuntimeError("ODIA startup did not create its managers.")

        # Create a second path of execution for voice recognition.
        # This lets voice work while the camera runs on the main thread.
        self.voice_thread = threading.Thread(
            # No (): give the thread the function to call later.
            target=self._run_voice,
            # A readable name helps when inspecting or debugging threads.
            name="VoiceTextWorker",
            # ⭐ IMPORTANT: the voice thread runs beside the main camera thread.
            # Normally, shutdown_event asks the voice thread to stop, and join()
            # waits for it. This lets both threads finish cleanly.
            #
            # With daemon=False, Python must wait for the voice thread to finish.
            # A stuck voice thread could therefore keep the whole program open.
            #
            # With daemon=True, the voice thread cannot keep Python alive alone.
            # If it gets stuck after the main thread ends, Python can still exit.
            # This is only a backup; daemon mode does not send a safe stop signal.
            daemon=True,
        )

        # Now start the thread. It begins by calling self._run_voice().
        self.voice_thread.start()

        # The original main thread continues here after starting voice work.
        try:
            # Open the camera and keep processing frames with YOLO.
            # This call keeps running until the camera closes or an error occurs.
            self.camera_manager.start_record()

        # If camera processing fails, show the error and its detailed traceback.
        except Exception as error:
            print(error)
            traceback.print_exc()

            # Tell the voice thread that it should stop too.
            self.shutdown_event.set()

        # Always clean up after the camera loop ends.
        finally:
            self.close()

    def _put_latest_classes(self, class_names: list[str]) -> None:
        """Keep only the newest voice request for the camera loop."""
        # Save when this request was created.
        # The camera can use the time to measure how long delivery took.
        requested_at = time.perf_counter()

        try:
            # Put the new request into the one-slot mailbox without waiting.
            # Example item: (["person", "bottle"], requested_at)
            self.class_names_queue.put_nowait((class_names, requested_at))

        # Full means one older voice request is still in the mailbox.
        except queue.Full:
            try:
                # Remove that older request to make room for the newest one.
                self.class_names_queue.get_nowait()
            except queue.Empty:
                # ⭐ THREAD TIMING: the camera removed it just before this line.
                # Another thread removed the old request first. That is okay.
                # Ignore the Empty error because the needed space already exists.
                pass

            # Add the newest request now that the mailbox has space.
            self.class_names_queue.put_nowait((class_names, requested_at))

    def _run_voice(self) -> None:
        """Read Whisper results and send matching classes to the camera."""
        # Safety check: voice work cannot run without its manager.
        if self.whisper_manager is None:
            return

        try:
            # Start the microphone stream and Whisper's audio worker.
            self.whisper_manager.start()
            print("음성 인식을 시작합니다.")
            print("종료하려면 Ctrl+C를 누르세요.")

            # Text_Manager matches spoken words to supported YOLO classes.
            # with closes Text_Manager automatically when voice work ends.
            with Text_Manager() as text_manager:
                # Keep listening until another part sets the shutdown signal.
                while not self.shutdown_event.is_set():
                    # Wait up to 0.5 seconds for Whisper to produce text.
                    # The short timeout lets this loop check shutdown regularly.
                    text = self.whisper_manager.get_transcribed_text(timeout=0.5)

                    # None means no new text arrived during that wait.
                    if text is None:
                        # Go back to the top of the while loop and try again.
                        continue

                    # Whisper returned text, so show what it heard.
                    print(f"음성 텍스트 수신: {text}")

                    # Find supported YOLO objects mentioned in that text.
                    # Example: "사람과 병" may produce person and bottle.
                    detected_classes = text_manager.extract(text)

                    # An empty list means no supported object name was found.
                    if not detected_classes:
                        print("일치하는 YOLO 클래스가 없습니다\n")

                        # Do not send anything to the camera. Listen again.
                        continue

                    # Send the matching English YOLO names to the camera mailbox.
                    self._put_latest_classes(
                        [detected.yolo_class for detected in detected_classes]
                    )

                    # Print each match so the user can see the conversion.
                    for detected in detected_classes:
                        print(
                            f"한국어={detected.korean_word}, "
                            f"class_name={detected.yolo_class}, "
                            f"class_id={detected.index}"
                        )
        # If voice or Whisper processing fails, show the error details.
        except Exception as error:
            print(error)
            traceback.print_exc()

            # Tell the camera loop to stop too.
            self.shutdown_event.set()

        # Always release the microphone and voice-model resources.
        finally:
            self.whisper_manager.close()

    def close(self) -> None:
        """Stop active work and release any resources that were created."""
        # Do not let prepare() and close() change resources at the same time.
        with self._lifecycle_lock:
            # run() and main.py may both call close().
            # If cleanup already happened, there is nothing more to do.
            if self._closed:
                return

            # Mark cleanup as started so another call cannot repeat it.
            self._closed = True

            # Ask both the camera loop and voice loop to stop.
            self.shutdown_event.set()

            # If the voice thread is running, wait up to five seconds for it.
            # Its own finally block closes the Whisper manager.
            if self.voice_thread is not None and self.voice_thread.is_alive():
                self.voice_thread.join(timeout=5.0)

            # If no voice thread is running, close Whisper directly if it exists.
            elif self.whisper_manager is not None:
                self.whisper_manager.close()

            # Release the camera and YOLO resources if they were created.
            if self.camera_manager is not None:
                self.camera_manager.unload()
