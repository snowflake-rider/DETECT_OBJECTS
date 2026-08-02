"""Whisper-machine entry point for distributed ODIA.

This machine owns the microphone and Whisper model. It converts recognized
Korean speech into YOLO class names and sends them to the YOLO machine.
"""

import argparse

from .comm import send_classes
from ..voice_text_convert.parse_and_match_module import Text_Manager


def process_transcript(
    transcript: str,
    yolo_address: str,
    text_manager: Text_Manager,
) -> None:
    """Convert one transcript into YOLO class names and send them."""
    # Example transcript: "사람과 백팩을 찾아줘"
    detected_classes = text_manager.extract(transcript)

    # Do not contact the YOLO machine when no class names were found.
    if not detected_classes:
        return

    # Change DetectedClass objects into a simple list of YOLO names.
    # Example result: ["person", "backpack"]
    class_names = [detected.yolo_class for detected in detected_classes]

    send_classes(yolo_address, class_names)


def run_whisper_node(
    yolo_address: str,
    microphone_id: int,
    model_name: str = "base",
) -> None:
    """Run Whisper and send recognized classes to the YOLO machine."""
    # Load the audio library only when this function starts.
    from ..voice_text_convert.mic_whisper_manager import Whisper_Audio_Manager

    # This manager owns the microphone, Whisper model, and audio worker thread.
    whisper_manager = Whisper_Audio_Manager(
        device_id=microphone_id,
        model_name=model_name,
    )

    try:
        # Start the microphone stream and Whisper worker.
        whisper_manager.start()

        # Load the Korean-to-YOLO dictionary once for the whole loop.
        with Text_Manager() as text_manager:
            while True:
                # Wait up to 0.5 seconds for Whisper to finish one transcript.
                transcript = whisper_manager.get_transcribed_text(timeout=0.5)

                # None means Whisper has no completed transcript yet.
                if transcript is None:
                    continue

                process_transcript(transcript, yolo_address, text_manager)
    except KeyboardInterrupt:
        # Ctrl+C is a normal request to stop this node.
        pass
    finally:
        # Always stop the stream, worker thread, and microphone.
        whisper_manager.close()


def main(argv: list[str] | None = None) -> int:
    """Read command-line options and start the Whisper node."""
    parser = argparse.ArgumentParser(
        description="Run Whisper and send classes to a YOLO machine."
    )

    # Full HTTP address of the YOLO machine.
    # Example: http://192.168.1.10:8000
    parser.add_argument("--yolo-address", required=True)

    # sounddevice uses this number to choose a microphone.
    parser.add_argument("--microphone-id", type=int, required=True)

    # Examples: tiny, base, small, medium, or large.
    parser.add_argument("--model-name", default="base")

    # Hyphens become underscores in the returned args object.
    args = parser.parse_args(argv)

    run_whisper_node(
        yolo_address=args.yolo_address,
        microphone_id=args.microphone_id,
        model_name=args.model_name,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
