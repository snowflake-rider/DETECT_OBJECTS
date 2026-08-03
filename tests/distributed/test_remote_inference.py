"""Tests for the application-facing remote inference seam."""

import base64
import unittest
from unittest.mock import MagicMock

import cv2
import numpy as np

from detect_objects.distributed.remote_inference import RemoteInference


class RemoteInferenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = MagicMock()
        self.client.submit.return_value = "job-1"
        self.remote = RemoteInference(self.client, timeout_seconds=5)

    def test_encodes_frame_and_returns_detections(self) -> None:
        self.client.wait.return_value = {
            "status": "succeeded",
            "result": {
                "detections": [
                    {
                        "bounds": [1, 2, 3, 4],
                        "class_name": "person",
                        "confidence": 0.9,
                    }
                ]
            },
        }
        frame = np.zeros((10, 20, 3), dtype=np.uint8)

        detections = self.remote.detect(frame, ["person"])

        capability, payload = self.client.submit.call_args.args
        decoded = cv2.imdecode(
            np.frombuffer(base64.b64decode(payload["image_jpeg_base64"]), np.uint8),
            cv2.IMREAD_COLOR,
        )
        self.assertEqual(capability, "vision:yolo_world_v2_small")
        self.assertEqual(decoded.shape, frame.shape)
        self.assertEqual(detections[0]["class_name"], "person")

    def test_encodes_float_audio_as_pcm16(self) -> None:
        self.client.wait.return_value = {
            "status": "succeeded",
            "result": {"text": "사람을 찾아줘"},
        }

        text = self.remote.transcribe(
            np.array([-1.0, 0.0, 1.0], dtype=np.float32),
            capability="voice:whisper_medium_ko",
        )

        capability, payload = self.client.submit.call_args.args
        samples = np.frombuffer(
            base64.b64decode(payload["audio_pcm16_base64"]),
            dtype="<i2",
        )
        self.assertEqual(capability, "voice:whisper_medium_ko")
        np.testing.assert_array_equal(samples, [-32767, 0, 32767])
        self.assertEqual(text, "사람을 찾아줘")

    def test_surfaces_remote_model_failure(self) -> None:
        self.client.wait.return_value = {
            "status": "failed",
            "error": "model out of memory",
        }

        with self.assertRaisesRegex(RuntimeError, "out of memory"):
            self.remote.transcribe(np.zeros(16, dtype=np.float32))


if __name__ == "__main__":
    unittest.main()
