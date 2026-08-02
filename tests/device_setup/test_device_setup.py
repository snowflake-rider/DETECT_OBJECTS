"""Tests for device discovery and UI-independent health checks."""

from __future__ import annotations

import unittest
from unittest.mock import patch

import cv2
import numpy as np
import sounddevice as sd
from cv2_enumerate_cameras.camera_info import CameraInfo

from device_setup.audio import (
    AudioInput,
    AudioInputInfo,
    AudioOutput,
    AudioOutputInfo,
)
from device_setup.camera import Camera
from device_setup.probe import (
    probe_audio_input,
    probe_audio_output,
    probe_camera,
)


class FakeFrame:
    """Provide the frame shape used by the camera probe."""

    shape = (720, 1280, 3)


class FakeCapture:
    """Simulate the OpenCV capture operations used by the camera probe."""

    def __init__(
        self,
        *,
        opened: bool,
        reads: list[tuple[bool, object | None]],
        fps: float = 0.0,
    ) -> None:
        self.opened = opened
        self.reads = iter(reads)
        self.fps = fps
        self.released = False

    def isOpened(self) -> bool:
        return self.opened

    def read(self) -> tuple[bool, object | None]:
        return next(self.reads, (False, None))

    def get(self, property_id: int) -> float:
        return self.fps

    def release(self) -> None:
        self.released = True


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
            patch("device_setup.camera.platform.system", return_value="Darwin"),
            patch(
                "device_setup.camera.supported_backends",
                [cv2.CAP_AVFOUNDATION],
            ),
            patch(
                "device_setup.camera.enumerate_cameras",
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
        with patch("device_setup.audio.sd.query_devices", return_value=self.devices):
            inputs = AudioInput.list_devices()

        self.assertEqual(
            inputs,
            [
                AudioInputInfo(0, "Microphone", 1, 16000.0),
                AudioInputInfo(2, "Headset", 1, 44100.0),
            ],
        )

    def test_lists_only_devices_with_output_channels(self) -> None:
        with patch("device_setup.audio.sd.query_devices", return_value=self.devices):
            outputs = AudioOutput.list_devices()

        self.assertEqual(
            outputs,
            [
                AudioOutputInfo(1, "Speakers", 2, 48000.0),
                AudioOutputInfo(2, "Headset", 2, 44100.0),
            ],
        )


class CameraProbeTests(unittest.TestCase):
    """Verify camera success, failure, retry, and cleanup behavior."""

    def setUp(self) -> None:
        camera_info = CameraInfo(
            2,
            "Test Camera",
            "/dev/test-camera",
            None,
            None,
            cv2.CAP_ANY,
        )
        self.camera = Camera(camera_info)

    def test_returns_frame_details_and_releases_capture(self) -> None:
        capture = FakeCapture(
            opened=True,
            reads=[(False, None), (True, FakeFrame())],
            fps=30.0,
        )

        with patch("device_setup.probe.cv2.VideoCapture", return_value=capture):
            result = probe_camera(self.camera, attempts=2)

        self.assertTrue(result.available)
        self.assertEqual(result.width, 1280)
        self.assertEqual(result.height, 720)
        self.assertEqual(result.fps, 30.0)
        self.assertTrue(capture.released)

    def test_reports_camera_that_cannot_open(self) -> None:
        capture = FakeCapture(opened=False, reads=[])

        with patch("device_setup.probe.cv2.VideoCapture", return_value=capture):
            result = probe_camera(self.camera)

        self.assertFalse(result.available)
        self.assertEqual(result.error, "Could not open camera.")
        self.assertTrue(capture.released)

    def test_reports_when_no_frame_is_received(self) -> None:
        capture = FakeCapture(opened=True, reads=[])

        with patch("device_setup.probe.cv2.VideoCapture", return_value=capture):
            result = probe_camera(self.camera, attempts=3)

        self.assertFalse(result.available)
        self.assertEqual(result.error, "No frame received after 3 attempt(s).")
        self.assertTrue(capture.released)

    def test_rejects_non_positive_attempts(self) -> None:
        with self.assertRaises(ValueError):
            probe_camera(self.camera, attempts=0)


class AudioProbeTests(unittest.TestCase):
    """Verify input sampling and output-tone submission."""

    def setUp(self) -> None:
        self.audio_input = AudioInput(
            AudioInputInfo(
                index=7,
                name="Test Microphone",
                channels=1,
                samplerate=8.0,
            )
        )
        self.audio_output = AudioOutput(
            AudioOutputInfo(
                index=8,
                name="Test Speakers",
                channels=2,
                samplerate=8000.0,
            )
        )

    def test_input_records_samples_and_reports_peak_level(self) -> None:
        samples = np.array([[0.25], [-0.5]], dtype=np.float32)

        with patch("device_setup.probe.sd.rec", return_value=samples) as record:
            result = probe_audio_input(self.audio_input, duration_seconds=0.25)

        self.assertTrue(result.available)
        self.assertAlmostEqual(result.peak_db, -6.0206, places=3)
        record.assert_called_once_with(
            2,
            samplerate=8.0,
            channels=1,
            device=7,
            dtype="float32",
            blocking=True,
        )

    def test_input_reports_portaudio_failure(self) -> None:
        with patch(
            "device_setup.probe.sd.rec",
            side_effect=sd.PortAudioError("input unavailable"),
        ):
            result = probe_audio_input(self.audio_input)

        self.assertFalse(result.available)
        self.assertIn("input unavailable", result.error)

    def test_output_submits_tone_to_selected_device(self) -> None:
        with patch("device_setup.probe.sd.play") as play:
            result = probe_audio_output(
                self.audio_output,
                duration_seconds=0.25,
                frequency_hz=440.0,
            )

        self.assertTrue(result.available)
        play.assert_called_once()
        tone = play.call_args.args[0]
        self.assertEqual(tone.shape, (2000,))
        self.assertAlmostEqual(float(np.abs(tone).max()), 0.1, places=6)
        self.assertEqual(play.call_args.kwargs["samplerate"], 8000.0)
        self.assertEqual(play.call_args.kwargs["device"], 8)
        self.assertTrue(play.call_args.kwargs["blocking"])

    def test_output_reports_portaudio_failure(self) -> None:
        with patch(
            "device_setup.probe.sd.play",
            side_effect=sd.PortAudioError("output unavailable"),
        ):
            result = probe_audio_output(self.audio_output)

        self.assertFalse(result.available)
        self.assertIn("output unavailable", result.error)

    def test_rejects_invalid_audio_probe_parameters(self) -> None:
        with self.assertRaises(ValueError):
            probe_audio_input(self.audio_input, duration_seconds=0)
        with self.assertRaises(ValueError):
            probe_audio_output(self.audio_output, duration_seconds=0)
        with self.assertRaises(ValueError):
            probe_audio_output(self.audio_output, frequency_hz=0)
        with self.assertRaises(ValueError):
            probe_audio_output(self.audio_output, frequency_hz=4000.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
