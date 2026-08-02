"""Tests for the combined microphone monitor and playback workflow."""

from __future__ import annotations

import unittest
from threading import Event
from unittest.mock import patch

import numpy as np

from audio_preview.microphone_preview import monitor_record_and_play
from device_setup import AudioInput, AudioInputInfo, AudioOutput, AudioOutputInfo


class FakeInputStream:
    """Provide recorded chunks through a fake PortAudio stream."""

    def __init__(self, chunks: list[np.ndarray], stop_event: Event, **kwargs) -> None:
        self.callback = kwargs["callback"]
        self.chunks = chunks
        self.stop_event = stop_event

    def __enter__(self) -> FakeInputStream:
        for chunk in self.chunks:
            self.callback(chunk, len(chunk), None, None)
        self.stop_event.set()
        return self

    def __exit__(self, exception_type, exception, traceback) -> None:
        return None


class MicrophonePreviewTests(unittest.TestCase):
    """Verify simultaneous levels, recording, stopping, and playback."""

    def setUp(self) -> None:
        self.audio_input = AudioInput(
            AudioInputInfo(
                index=7,
                name="Test Microphone",
                channels=1,
                samplerate=4.0,
            )
        )
        self.audio_output = AudioOutput(
            AudioOutputInfo(
                index=8,
                name="Test Speakers",
                channels=2,
                samplerate=48000.0,
            )
        )

    def test_monitors_records_and_plays_after_stop(self) -> None:
        stop_event = Event()
        chunks = [
            np.array([[0.25], [-0.25]], dtype=np.float32),
            np.array([[0.5], [-0.5]], dtype=np.float32),
        ]
        levels: list[float] = []

        def input_stream(**kwargs):
            return FakeInputStream(chunks, stop_event, **kwargs)

        with (
            patch(
                "audio_preview.microphone_preview.sd.InputStream",
                side_effect=input_stream,
            ),
            patch("audio_preview.microphone_preview.sd.play") as play,
        ):
            result = monitor_record_and_play(
                self.audio_input,
                self.audio_output,
                stop_event,
                levels.append,
            )

        self.assertTrue(result.successful)
        self.assertEqual(len(levels), 2)
        self.assertEqual(result.duration_seconds, 1.0)
        self.assertAlmostEqual(result.peak_db, -6.0206, places=3)
        recording = play.call_args.args[0]
        np.testing.assert_array_equal(recording, np.concatenate(chunks))
        self.assertEqual(play.call_args.kwargs["samplerate"], 4.0)
        self.assertEqual(play.call_args.kwargs["device"], 8)
        self.assertTrue(play.call_args.kwargs["blocking"])

    def test_reports_when_stream_produces_no_samples(self) -> None:
        stop_event = Event()

        def input_stream(**kwargs):
            return FakeInputStream([], stop_event, **kwargs)

        with patch(
            "audio_preview.microphone_preview.sd.InputStream",
            side_effect=input_stream,
        ):
            result = monitor_record_and_play(
                self.audio_input,
                self.audio_output,
                stop_event,
                lambda level: None,
            )

        self.assertFalse(result.successful)
        self.assertEqual(result.error, "No audio samples were received.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
