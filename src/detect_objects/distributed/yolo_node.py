"""YOLO-machine entry point for distributed ODIA.

This machine owns the camera and YOLO model. It receives class names from the
Whisper machine and asks the existing camera manager to detect those classes.
"""

import argparse
import queue
import threading
import time

from .comm import receive_classes
from ..voice_text_convert.parse_and_match_module import Text_Manager


def update_classes(
    class_names: list[str],
    class_queue: queue.Queue[tuple[list[str], float]],
) -> None:
    """Put the newest class names into the camera queue."""
    # Whole process:
    # 1. The HTTP server receives class_names from the Whisper machine.
    # 2. This function puts them into class_queue.
    # 3. The camera loop takes them from class_queue.
    # 4. YOLO changes which objects it detects.

    # class_queue safely passes data from the HTTP thread to the camera loop.
    #
    # Method        Meaning here                              If it cannot run
    # ------------  ----------------------------------------  ------------------
    # put_nowait    Put class_request into class_queue now    Raises queue.Full
    # get_nowait    Get and remove the oldest queue item now  Raises queue.Empty
    #
    # "put" means add to the queue. "get" means take from the queue.
    # "nowait" means the HTTP thread continues immediately instead of waiting.

    # class_request stores the classes and the time they arrived.
    # The camera uses the time to measure how long the update took.
    class_request = (class_names, time.perf_counter())

    # Possible cases:
    #
    # Case  Queue before adding  What happens
    # ----  -------------------  ---------------------------------------------
    # 1     Empty                put_nowait adds the new request. No exception.
    # 2     Full                 put_nowait raises Full. We remove the old
    #                            request, then add the new request.
    # 3     Full                 put_nowait raises Full, but the camera removes
    #                            the old request before get_nowait. get_nowait
    #                            raises Empty, so we skip removal and add the
    #                            new request.

    try:
        # put_nowait adds data immediately. It never pauses to wait for space.
        class_queue.put_nowait(class_request)
    except queue.Full:
        # Remove the old request because only the newest one matters.
        #
        # HTTP thread                 Camera loop
        # -----------                 -----------
        # put_nowait -> Full
        #                             removes old request
        # get_nowait -> Empty
        #
        # The queue changed between the two HTTP-thread operations.
        try:
            # get_nowait removes data immediately. It never waits for data.
            class_queue.get_nowait()
        except queue.Empty:
            # ⭐ IMPORTANT: queue.Empty is expected here and is safe to ignore.
            # The camera already removed it. That is okay, so do nothing.
            # Catching Empty prevents the function from stopping with an error.
            # This handles the expected exception: pass means ignore and continue.
            pass

        # The queue now has space for the newest request.
        class_queue.put_nowait(class_request)


def run_yolo_node(host: str, port: int, camera_index: int) -> None:
    """Run the HTTP receiver and camera detection on the YOLO machine."""
    # 1. Load Camera_Manager only when this function starts.
    # Importing this here avoids loading camera and AI libraries until needed.
    from ..camera_cv.camera_cv import Camera_Manager

    # 2. Create the queue shared by the HTTP receiver and camera loop.
    #
    # class_queue is a thread-safe queue.Queue.
    # The HTTP thread puts class requests into it.
    # The camera loop gets class requests from it.
    #
    # One queue item looks like this:
    # (["person", "backpack"], 123.45)
    #  └─ class names              └─ time received
    #
    # maxsize=1 keeps only one waiting request: the newest request.
    class_queue: queue.Queue[tuple[list[str], float]] = queue.Queue(maxsize=1)

    # 3. Create one shutdown signal shared by both parts.
    #
    # shutdown_event has type threading.Event.
    # It is a thread-safe flag with two states:
    #
    # is_set() == False  -> keep running
    # is_set() == True   -> stop running
    #
    # shutdown_event.set() changes the flag to True.
    # It is set when the camera closes, the user quits, or an error occurs.
    shutdown_event = threading.Event()

    # 4. Define what happens when class names arrive over HTTP.
    #
    # receive_classes calls on_classes_received with data such as:
    # class_names = ["person", "backpack"]
    #
    # on_classes_received then calls update_classes.
    # update_classes puts the names and arrival time into class_queue.
    def on_classes_received(class_names: list[str]) -> None:
        update_classes(class_names, class_queue)

    # 5. Read every class that the Korean word dictionary can produce.
    # YOLO caches these classes once, before the camera loop starts.
    with Text_Manager() as text_manager:
        supported_classes = text_manager.get_supported_yolo_classes()

    # 6. Give Camera_Manager the camera, queue, event, and supported classes.
    # Camera_Manager checks class_queue between camera frames.
    camera_manager = Camera_Manager(
        camera_index=camera_index,
        thread_event=shutdown_event,
        class_names_queue=class_queue,
        supported_classes=supported_classes,
    )

    # 7. Prepare a background thread for the HTTP receiver.
    #
    # target is the function the thread runs.
    # args are the values passed to receive_classes.
    # daemon=True allows Python to exit if this thread is still waiting.
    # HTTP waits here while the camera runs on the main thread.
    receiver_thread = threading.Thread(
        target=receive_classes,
        args=(host, port, on_classes_received, shutdown_event),
        name="ClassReceiver",
        daemon=True,
    )

    # Start listening for messages from the Whisper machine.
    receiver_thread.start()

    # 8. Load YOLO, then start reading camera frames.
    # start_record keeps running until:
    # - the user presses q,
    # - the camera cannot read a frame,
    # - shutdown_event is set, or
    # - an error occurs.
    try:
        camera_manager.load_model()
        camera_manager.start_record()
    finally:
        # 9. This cleanup runs after a normal exit or an error.
        # Python enters finally when load_model or start_record finishes or fails.
        # set() tells the HTTP receiver and camera loop to stop.
        shutdown_event.set()

        # Release the camera, YOLO model, and OpenCV windows.
        camera_manager.unload()

        # Wait up to one second for the HTTP receiver thread to finish.
        receiver_thread.join(timeout=1)


def main(argv: list[str] | None = None) -> int:
    """Read command-line options and start the YOLO node."""
    # General argparse process:
    #
    # Command text
    #   --host 0.0.0.0 --port 8000 --camera-index 0
    #                         |
    #                         v
    # ArgumentParser uses the add_argument rules below
    #                         |
    #                         v
    # args.host, args.port, and args.camera_index
    #                         |
    #                         v
    # run_yolo_node(...)

    # argparse is Python's command-line argument module.
    # ArgumentParser stores the rules and creates the --help page.
    # description is the sentence shown near the top of that help page.
    #
    # Parser after this line:
    # - knows the program description
    # - automatically supports -h and --help
    parser = argparse.ArgumentParser(
        description="Run the camera and YOLO receiver on this machine."
    )

    # add_argument tells the parser which option is allowed.
    # 0.0.0.0 accepts connections through any network address on this machine.
    parser.add_argument("--host", default="0.0.0.0")
    # Parser now knows:
    # - --help
    # - --host HOST, which is optional and defaults to 0.0.0.0

    # type=int changes the command-line text into a Python integer.
    # Whisper sends class names to this HTTP port.
    parser.add_argument("--port", type=int, default=8000)
    # Parser now also knows:
    # - --port PORT, which is optional, must be an integer, and defaults to 8000

    # required=True means the user must provide this option.
    # OpenCV uses this number to choose a camera.
    parser.add_argument("--camera-index", type=int, required=True)
    # Final parser rules:
    # - --help: show help
    # - --host: optional string
    # - --port: optional integer
    # - --camera-index: required integer

    # Example argv: ["--host", "0.0.0.0", "--port", "8000",
    #                "--camera-index", "0"]
    #
    # parse_args reads argv and checks it against the rules above.
    # If argv is None, it reads the real terminal command instead.
    # It returns an object named args. Hyphens become underscores, so
    # --camera-index becomes args.camera_index.
    args = parser.parse_args(argv)

    run_yolo_node(
        host=args.host,
        port=args.port,
        camera_index=args.camera_index,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
