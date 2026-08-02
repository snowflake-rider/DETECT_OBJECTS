"""Tests for device discovery and UI-independent health checks."""

from __future__ import annotations

import unittest
from threading import Event
from unittest.mock import patch

import cv2
import numpy as np
import sounddevice as sd
from cv2_enumerate_cameras.camera_info import CameraInfo

from detect_objects.device_setup.audio import (
    AudioInput,
    AudioInputInfo,
    AudioOutput,
    AudioOutputInfo,
)
from detect_objects.device_setup.camera import Camera
from detect_objects.device_setup.probe import (
    AudioRecording,
    monitor_and_record,
    play_recording,
    probe_audio_output,
)


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


class CameraDiscoveryTests(unittest.TestCase):
    """Verify camera enumeration through the platform backend."""

    def test_lists_cameras_from_preferred_backend(self) -> None:
        camera_info = CameraInfo(
            2,
            "Test Camera",
            "/dev/test-camera",
            None,
            None,
            cv2.CAP_AVFOUNDATION,
        )

        with (
            patch(
                "detect_objects.device_setup.camera.platform.system",
                return_value="Darwin",
            ),
            patch(
                "detect_objects.device_setup.camera.supported_backends",
                [cv2.CAP_AVFOUNDATION],
            ),
            patch(
                "detect_objects.device_setup.camera.enumerate_cameras",
                return_value=[camera_info],
            ) as enumerate_devices,
        ):
            cameras = Camera.list_devices()

        self.assertEqual(cameras, [camera_info])
        enumerate_devices.assert_called_once_with(cv2.CAP_AVFOUNDATION)


class AudioDiscoveryTests(unittest.TestCase):
    """Verify that audio devices are separated by their channel direction."""

    def setUp(self) -> None:
        self.devices = [
            {
                "name": "Microphone",
                "max_input_channels": 1,
                "max_output_channels": 0,
                "default_samplerate": 16000.0,
            },
            {
                "name": "Speakers",
                "max_input_channels": 0,
                "max_output_channels": 2,
                "default_samplerate": 48000.0,
            },
            {
                "name": "Headset",
                "max_input_channels": 1,
                "max_output_channels": 2,
                "default_samplerate": 44100.0,
            },
        ]

    def test_lists_only_devices_with_input_channels(self) -> None:
        with patch(
            "detect_objects.device_setup.audio.sd.query_devices",
            return_value=self.devices,
        ):
            inputs = AudioInput.list_devices()

        self.assertEqual(
            inputs,
            [
                AudioInputInfo(0, "Microphone", 1, 16000.0),
                AudioInputInfo(2, "Headset", 1, 44100.0),
            ],
        )

    def test_lists_only_devices_with_output_channels(self) -> None:
        with patch(
            "detect_objects.device_setup.audio.sd.query_devices",
            return_value=self.devices,
        ):
            outputs = AudioOutput.list_devices()

        self.assertEqual(
            outputs,
            [
                AudioOutputInfo(1, "Speakers", 2, 48000.0),
                AudioOutputInfo(2, "Headset", 2, 44100.0),
            ],
        )


class AudioProbeTests(unittest.TestCase):
    """Verify output-sample submission."""

    def setUp(self) -> None:
        self.audio_output = AudioOutput(
            AudioOutputInfo(
                index=8,
                name="Test Speakers",
                channels=2,
                samplerate=8000.0,
            )
        )

    def test_output_submits_first_five_seconds_to_selected_device(self) -> None:
        samples = np.arange(24, dtype=np.float32)
        with (
            patch(
                "detect_objects.device_setup.probe.sf.read",
                return_value=(samples, 4),
            ) as read,
            patch("detect_objects.device_setup.probe.sd.play") as play,
        ):
            result = probe_audio_output(self.audio_output)

        self.assertTrue(result.available)
        read.assert_called_once()
        self.assertEqual(read.call_args.args[0].name, "cat_meow.wav")
        self.assertEqual(read.call_args.kwargs["dtype"], "float32")
        play.assert_called_once()
        np.testing.assert_array_equal(play.call_args.args[0], samples[:20])
        self.assertEqual(play.call_args.kwargs["samplerate"], 4)
        self.assertEqual(play.call_args.kwargs["device"], 8)
        self.assertTrue(play.call_args.kwargs["blocking"])

    def test_output_reports_portaudio_failure(self) -> None:
        samples = np.array([0.0], dtype=np.float32)
        with (
            patch(
                "detect_objects.device_setup.probe.sf.read",
                return_value=(samples, 16000),
            ),
            patch(
                "detect_objects.device_setup.probe.sd.play",
                side_effect=sd.PortAudioError("output unavailable"),
            ),
        ):
            result = probe_audio_output(self.audio_output)

        self.assertFalse(result.available)
        self.assertIn("output unavailable", result.error)

    def test_output_reports_cat_sample_loading_failure(self) -> None:
        with patch(
            "detect_objects.device_setup.probe.sf.read",
            side_effect=OSError("sample missing"),
        ):
            result = probe_audio_output(self.audio_output)

        self.assertFalse(result.available)
        self.assertIn("Could not load cat sample", result.error)


class AudioRecordingTests(unittest.TestCase):
    """Verify that monitored recording and playback remain separate operations."""

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

    def test_monitors_and_retains_recording_after_stop(self) -> None:
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
                "detect_objects.device_setup.probe.sd.InputStream",
                side_effect=input_stream,
            ),
            patch("detect_objects.device_setup.probe.sd.play") as play,
        ):
            result = monitor_and_record(
                self.audio_input,
                stop_event,
                levels.append,
            )

        self.assertTrue(result.successful)
        self.assertEqual(len(levels), 2)
        self.assertIsNotNone(result.recording)
        recording = result.recording
        self.assertEqual(recording.duration_seconds, 1.0)
        self.assertAlmostEqual(recording.peak_db, -6.0206, places=3)
        np.testing.assert_array_equal(recording.samples, np.concatenate(chunks))
        play.assert_not_called()

    def test_plays_retained_recording_through_selected_output(self) -> None:
        recording = AudioRecording(
            samples=np.array([[0.5], [-0.5]], dtype=np.float32),
            samplerate=4.0,
            duration_seconds=0.5,
            peak_db=-6.0206,
        )

        with patch("detect_objects.device_setup.probe.sd.play") as play:
            playback_result = play_recording(recording, self.audio_output)

        self.assertTrue(playback_result.successful)
        np.testing.assert_array_equal(play.call_args.args[0], recording.samples)
        self.assertEqual(play.call_args.kwargs["samplerate"], 4.0)
        self.assertEqual(play.call_args.kwargs["device"], 8)
        self.assertTrue(play.call_args.kwargs["blocking"])

    def test_reports_when_stream_produces_no_samples(self) -> None:
        stop_event = Event()

        def input_stream(**kwargs):
            return FakeInputStream([], stop_event, **kwargs)

        with patch(
            "detect_objects.device_setup.probe.sd.InputStream",
            side_effect=input_stream,
        ):
            result = monitor_and_record(
                self.audio_input,
                stop_event,
                lambda level: None,
            )

        self.assertFalse(result.successful)
        self.assertEqual(result.error, "No audio samples were received.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
