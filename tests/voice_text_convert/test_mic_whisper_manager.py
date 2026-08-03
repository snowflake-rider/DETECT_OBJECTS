"""Tests for voice activity detection in the Whisper audio manager."""

import unittest

import numpy as np

from detect_objects.voice_text_convert.mic_whisper_manager import (
    Whisper_Audio_Manager,
)


class VoiceActivityDetectionTests(unittest.TestCase):
    def create_manager(self, **overrides) -> Whisper_Audio_Manager:
        options = {
            "device_id": 0,
            "sample_rate": 10,
            "channels": 1,
            "record_seconds": 2,
            "block_size": 2,
            "vad_threshold": 0.5,
            "vad_silence_seconds": 0.4,
            "vad_min_speech_seconds": 0.2,
            "vad_pre_roll_seconds": 0.4,
        }
        options.update(overrides)
        return Whisper_Audio_Manager(**options)

    @staticmethod
    def enqueue(manager: Whisper_Audio_Manager, *blocks: np.ndarray) -> None:
        for block in blocks:
            manager._audio_callback(block, len(block), None, None)

    def test_collects_pre_roll_and_stops_after_sustained_silence(self) -> None:
        manager = self.create_manager()
        silence = np.zeros((2, 1), dtype=np.float32)
        speech = np.ones((2, 1), dtype=np.float32)
        self.enqueue(manager, silence, speech, silence, silence)

        audio = manager.collect_audio()

        self.assertIsNotNone(audio)
        self.assertEqual(audio.dtype, np.float32)
        np.testing.assert_array_equal(
            audio,
            np.array([0, 0, 1, 1, 0, 0, 0, 0], dtype=np.float32),
        )

    def test_stops_at_maximum_utterance_length(self) -> None:
        manager = self.create_manager(
            record_seconds=0.6,
            vad_silence_seconds=1.0,
            vad_pre_roll_seconds=0.0,
        )
        speech = np.ones((2, 1), dtype=np.float32)
        self.enqueue(manager, speech, speech, speech)

        audio = manager.collect_audio()

        self.assertEqual(len(audio), 6)

    def test_rejects_invalid_vad_settings(self) -> None:
        invalid_settings = (
            {"vad_threshold": 0},
            {"vad_silence_seconds": 0},
            {"vad_min_speech_seconds": -0.1},
            {"vad_pre_roll_seconds": -0.1},
        )

        for settings in invalid_settings:
            with self.subTest(settings=settings), self.assertRaises(ValueError):
                self.create_manager(**settings)


if __name__ == "__main__":
    unittest.main()
