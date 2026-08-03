"""Application-facing interface for remote vision and voice inference."""

from __future__ import annotations

import base64
from typing import Any, Sequence

import cv2
import numpy as np

from .client import ClusterClient
from .model_handlers import YOLO_CAPABILITY


class RemoteInference:
    """Hide job submission, polling, and binary encoding from model callers."""

    def __init__(self, client: ClusterClient, *, timeout_seconds: float = 300.0) -> None:
        self._client = client
        self._timeout_seconds = timeout_seconds

    def detect(
        self,
        frame: np.ndarray,
        classes: Sequence[str],
        *,
        capability: str = YOLO_CAPABILITY,
        jpeg_quality: int = 85,
    ) -> list[dict[str, Any]]:
        """Run object detection on a remote worker and return pixel detections."""
        if not isinstance(frame, np.ndarray) or frame.ndim != 3:
            raise ValueError("frame must be a color numpy array")
        if not classes:
            raise ValueError("classes cannot be empty")
        if not 1 <= jpeg_quality <= 100:
            raise ValueError("jpeg_quality must be between 1 and 100")
        encoded_ok, encoded = cv2.imencode(
            ".jpg",
            frame,
            [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality],
        )
        if not encoded_ok:
            raise ValueError("unable to encode frame as JPEG")
        payload = {
            "image_jpeg_base64": base64.b64encode(encoded).decode("ascii"),
            "classes": list(classes),
        }
        result = self._run(capability, payload)
        detections = result.get("detections")
        if not isinstance(detections, list):
            raise RuntimeError("vision worker returned an invalid result")
        return detections

    def transcribe(
        self,
        audio: np.ndarray,
        *,
        capability: str = "voice:whisper_large-v3_ko",
        sample_rate: int = 16000,
    ) -> str:
        """Transcribe mono floating-point audio on a remote Whisper worker."""
        if not isinstance(audio, np.ndarray) or audio.ndim != 1:
            raise ValueError("audio must be a one-dimensional numpy array")
        if sample_rate != 16000:
            raise ValueError("remote Whisper currently requires 16000 Hz audio")
        clipped = np.clip(audio, -1.0, 1.0)
        pcm16 = (clipped * 32767.0).astype("<i2", copy=False)
        payload = {
            "audio_pcm16_base64": base64.b64encode(pcm16.tobytes()).decode("ascii"),
            "sample_rate": sample_rate,
        }
        result = self._run(capability, payload)
        text = result.get("text")
        if not isinstance(text, str):
            raise RuntimeError("voice worker returned an invalid result")
        return text

    def _run(self, capability: str, payload: dict[str, Any]) -> dict[str, Any]:
        job_id = self._client.submit(capability, payload)
        job = self._client.wait(job_id, timeout_seconds=self._timeout_seconds)
        if job["status"] != "succeeded":
            raise RuntimeError(job.get("error") or "remote inference failed")
        result = job.get("result")
        if not isinstance(result, dict):
            raise RuntimeError("model worker returned an invalid result")
        return result
