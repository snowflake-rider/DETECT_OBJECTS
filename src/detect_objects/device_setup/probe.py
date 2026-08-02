"""UI-independent audio tests for selected input and output devices."""

from __future__ import annotations

import math
from dataclasses import dataclass
from threading import Event
from typing import Callable

import numpy as np
import sounddevice as sd
import soundfile as sf

from .audio import AudioInput, AudioOutput
from ..paths import PROJECT_ROOT

CAT_MEOW_PATH = PROJECT_ROOT / "samples" / "audio" / "cat_meow.wav"
CAT_MEOW_SECONDS = 5.0


@dataclass(frozen=True)
class AudioOutputProbeResult:
    """Outcome from submitting the bundled cat sample to one audio output."""

    available: bool
    error: str | None = None


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


def probe_audio_output(
    audio_output: AudioOutput,
) -> AudioOutputProbeResult:
    """Play five seconds of the cat meow; success does not confirm it was heard."""
    try:
        meow, samplerate = sf.read(CAT_MEOW_PATH, dtype="float32")
    except (OSError, sf.SoundFileError) as error:
        return AudioOutputProbeResult(
            available=False,
            error=f"Could not load cat sample: {error}",
        )

    frame_count = max(1, round(samplerate * CAT_MEOW_SECONDS))
    meow = meow[:frame_count]

    try:
        sd.play(
            meow,
            samplerate=samplerate,
            device=audio_output.info.index,
            blocking=True,
        )
    except (sd.PortAudioError, TypeError, ValueError) as error:
        return AudioOutputProbeResult(
            available=False,
            error=f"Audio output test failed: {error}",
        )

    return AudioOutputProbeResult(available=True)


def _rms_decibels(samples: np.ndarray) -> float:
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
