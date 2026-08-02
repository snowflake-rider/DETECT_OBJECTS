"""UI-independent health checks for selected camera and audio devices."""

from __future__ import annotations

import math
from dataclasses import dataclass

import cv2
import numpy as np
import sounddevice as sd

from .audio import AudioInput, AudioOutput
from .camera import Camera


@dataclass(frozen=True)
class CameraProbeResult:
    """Outcome and frame details from one camera health check."""

    available: bool
    width: int | None = None
    height: int | None = None
    fps: float | None = None
    error: str | None = None


@dataclass(frozen=True)
class AudioInputProbeResult:
    """Outcome and peak level from one audio-input health check."""

    available: bool
    peak_db: float | None = None
    error: str | None = None


@dataclass(frozen=True)
class AudioOutputProbeResult:
    """Outcome from submitting a test tone to one audio output."""

    available: bool
    error: str | None = None


def probe_camera(camera: Camera, attempts: int = 5) -> CameraProbeResult:
    """Open a camera, try to read a frame, and always release it."""
    if attempts < 1:
        raise ValueError("attempts must be positive")

    try:
        capture = cv2.VideoCapture(
            camera.info.index,
            camera.info.backend,
        )
    except (cv2.error, TypeError, ValueError) as error:
        return CameraProbeResult(
            available=False,
            error=f"Could not create camera capture: {error}",
        )

    try:
        if not capture.isOpened():
            return CameraProbeResult(
                available=False,
                error="Could not open camera.",
            )

        for _ in range(attempts):
            success, frame = capture.read()
            if not success or frame is None:
                continue

            height, width = frame.shape[:2]
            fps = float(capture.get(cv2.CAP_PROP_FPS))
            if not math.isfinite(fps) or fps <= 0:
                fps = None

            return CameraProbeResult(
                available=True,
                width=int(width),
                height=int(height),
                fps=fps,
            )

        return CameraProbeResult(
            available=False,
            error=f"No frame received after {attempts} attempt(s).",
        )
    except (cv2.error, TypeError, ValueError) as error:
        return CameraProbeResult(
            available=False,
            error=f"Camera test failed: {error}",
        )
    finally:
        capture.release()


def probe_audio_input(
    audio_input: AudioInput,
    duration_seconds: float = 0.25,
) -> AudioInputProbeResult:
    """Record a short sample and report whether the input supplied audio data."""
    if duration_seconds <= 0:
        raise ValueError("duration_seconds must be positive")

    frame_count = max(1, round(audio_input.info.samplerate * duration_seconds))
    try:
        samples = sd.rec(
            frame_count,
            samplerate=audio_input.info.samplerate,
            channels=1,
            device=audio_input.info.index,
            dtype="float32",
            blocking=True,
        )
    except (sd.PortAudioError, TypeError, ValueError) as error:
        return AudioInputProbeResult(
            available=False,
            error=f"Audio input test failed: {error}",
        )

    samples = np.asarray(samples)
    if samples.size == 0:
        return AudioInputProbeResult(
            available=False,
            error="No audio samples were received.",
        )

    peak = float(np.abs(samples).max(initial=0.0))
    return AudioInputProbeResult(
        available=True,
        peak_db=20 * math.log10(max(peak, 1e-10)),
    )


def probe_audio_output(
    audio_output: AudioOutput,
    duration_seconds: float = 0.9,
    frequency_hz: float = 440.0,
) -> AudioOutputProbeResult:
    """Play a cat-like meow; success confirms submission, not that it was heard."""
    if duration_seconds <= 0:
        raise ValueError("duration_seconds must be positive")
    if frequency_hz <= 0:
        raise ValueError("frequency_hz must be positive")
    if frequency_hz >= audio_output.info.samplerate / 2:
        raise ValueError("frequency_hz must be below the output Nyquist frequency")

    frame_count = max(1, round(audio_output.info.samplerate * duration_seconds))
    times = np.arange(frame_count, dtype=np.float32) / audio_output.info.samplerate
    progress = times / duration_seconds
    glide = 1.55 - 0.85 * progress + 0.08 * np.sin(4 * math.pi * progress)
    instantaneous_frequency = frequency_hz * glide
    phase = 2 * math.pi * np.cumsum(instantaneous_frequency) / audio_output.info.samplerate
    voice = np.sin(phase) + 0.35 * np.sin(2 * phase) + 0.12 * np.sin(3 * phase)
    envelope = np.sin(math.pi * np.clip(progress, 0.0, 1.0)) ** 1.5
    meow = (0.08 * envelope * voice).astype(np.float32)

    try:
        sd.play(
            meow,
            samplerate=audio_output.info.samplerate,
            device=audio_output.info.index,
            blocking=True,
        )
    except (sd.PortAudioError, TypeError, ValueError) as error:
        return AudioOutputProbeResult(
            available=False,
            error=f"Audio output test failed: {error}",
        )

    return AudioOutputProbeResult(available=True)
