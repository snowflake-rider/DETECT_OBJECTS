"""Record, monitor, and play back a selected audio input."""

from __future__ import annotations

import math
from dataclasses import dataclass
from threading import Event
from typing import Callable

import numpy as np
import sounddevice as sd

from device_setup import AudioInput, AudioOutput


@dataclass(frozen=True)
class AudioRecording:
    """Captured mono samples and measurements retained for playback."""

    samples: np.ndarray
    samplerate: float
    duration_seconds: float
    peak_db: float


@dataclass(frozen=True)
class RecordingResult:
    """Outcome returned after monitoring and recording finish."""

    successful: bool
    recording: AudioRecording | None = None
    error: str | None = None


@dataclass(frozen=True)
class PlaybackResult:
    """Outcome returned after playing a retained recording."""

    successful: bool
    error: str | None = None


def _rms_decibels(samples) -> float:
    """Calculate an RMS input level in decibels."""
    rms = math.sqrt(float((samples**2).mean()))
    return 20 * math.log10(max(rms, 1e-10))


def monitor_and_record(
    audio_input: AudioInput,
    stop_event: Event,
    on_level: Callable[[float], None],
) -> RecordingResult:
    """Monitor input levels and record until the caller requests a stop."""
    chunks: list[np.ndarray] = []
    peak_level = 0.0

    def record(indata, frames, time_info, status) -> None:
        nonlocal peak_level
        samples = indata.copy()
        chunks.append(samples)
        peak_level = max(peak_level, float(np.abs(samples).max(initial=0.0)))
        try:
            on_level(_rms_decibels(samples))
        except Exception:
            # PortAudio callbacks must return quickly and must not leak UI errors.
            return

    try:
        with sd.InputStream(
            device=audio_input.info.index,
            channels=1,
            samplerate=audio_input.info.samplerate,
            callback=record,
        ):
            stop_event.wait()
    except (sd.PortAudioError, TypeError, ValueError) as error:
        return RecordingResult(
            successful=False,
            error=f"Microphone recording failed: {error}",
        )

    if not chunks:
        return RecordingResult(
            successful=False,
            error="No audio samples were received.",
        )

    samples = np.concatenate(chunks, axis=0)
    recording = AudioRecording(
        samples=samples,
        samplerate=audio_input.info.samplerate,
        duration_seconds=len(samples) / audio_input.info.samplerate,
        peak_db=20 * math.log10(max(peak_level, 1e-10)),
    )
    return RecordingResult(successful=True, recording=recording)


def play_recording(
    recording: AudioRecording,
    audio_output: AudioOutput,
) -> PlaybackResult:
    """Play a retained recording through the selected audio output."""
    try:
        sd.play(
            recording.samples,
            samplerate=recording.samplerate,
            device=audio_output.info.index,
            blocking=True,
        )
    except (sd.PortAudioError, TypeError, ValueError) as error:
        return PlaybackResult(
            successful=False,
            error=f"Recording playback failed: {error}",
        )

    return PlaybackResult(successful=True)
