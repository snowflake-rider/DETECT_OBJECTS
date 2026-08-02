"""Tests for the distributed Whisper node."""

import sys
from types import SimpleNamespace
from types import ModuleType
import unittest
from unittest.mock import MagicMock, patch

from detect_objects.distributed import whisper_node
from detect_objects.distributed.whisper_node import (
    main,
    process_transcript,
    run_whisper_node,
)


class ProcessTranscriptTests(unittest.TestCase):
    @patch.object(whisper_node, "send_classes")
    def test_sends_matching_yolo_classes(self, send_classes) -> None:
        text_manager = MagicMock()
        text_manager.extract.return_value = [
            SimpleNamespace(yolo_class="person"),
            SimpleNamespace(yolo_class="backpack"),
        ]

        process_transcript(
            "사람과 백팩을 찾아줘",
            "http://192.168.1.10:8000",
            text_manager,
        )

        send_classes.assert_called_once_with(
            "http://192.168.1.10:8000",
            ["person", "backpack"],
        )

    @patch.object(whisper_node, "send_classes")
    def test_does_not_send_when_no_classes_match(self, send_classes) -> None:
        text_manager = MagicMock()
        text_manager.extract.return_value = []

        process_transcript(
            "오늘 날씨가 좋아",
            "http://192.168.1.10:8000",
            text_manager,
        )

        send_classes.assert_not_called()


class RunWhisperNodeTests(unittest.TestCase):
    @patch.object(whisper_node, "process_transcript")
    @patch.object(whisper_node, "Text_Manager")
    def test_processes_transcripts_and_closes_manager(
        self,
        text_manager_class,
        process_transcript,
    ) -> None:
        text_manager = text_manager_class.return_value.__enter__.return_value

        whisper_manager = MagicMock()
        whisper_manager.get_transcribed_text.side_effect = [
            "사람을 찾아줘",
            KeyboardInterrupt,
        ]
        whisper_manager_class = MagicMock(return_value=whisper_manager)
        whisper_module = ModuleType(
            "detect_objects.voice_text_convert.mic_whisper_manager"
        )
        whisper_module.Whisper_Audio_Manager = whisper_manager_class

        with patch.dict(
            sys.modules,
            {
                "detect_objects.voice_text_convert.mic_whisper_manager": (
                    whisper_module
                )
            },
        ):
            run_whisper_node(
                "http://192.168.1.10:8000",
                microphone_id=4,
                model_name="medium",
            )

        whisper_manager_class.assert_called_once_with(
            device_id=4,
            model_name="medium",
        )
        whisper_manager.start.assert_called_once_with()
        process_transcript.assert_called_once_with(
            "사람을 찾아줘",
            "http://192.168.1.10:8000",
            text_manager,
        )
        whisper_manager.close.assert_called_once_with()


class MainTests(unittest.TestCase):
    @patch.object(whisper_node, "run_whisper_node")
    def test_starts_whisper_node_with_command_line_options(self, run_node) -> None:
        exit_code = main(
            [
                "--yolo-address",
                "http://192.168.1.10:8000",
                "--microphone-id",
                "4",
                "--model-name",
                "medium",
            ]
        )

        self.assertEqual(exit_code, 0)
        run_node.assert_called_once_with(
            yolo_address="http://192.168.1.10:8000",
            microphone_id=4,
            model_name="medium",
        )


if __name__ == "__main__":
    unittest.main()
