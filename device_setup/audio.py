"""Discover audio input devices and store a selected microphone."""

from __future__ import annotations

from dataclasses import dataclass

import sounddevice as sd


@dataclass(frozen=True)
class AudioInfo:
    """Information needed to identify and open one microphone."""

    # This index is the value sounddevice expects when opening an input stream.
    index: int
    name: str
    channels: int
    samplerate: float


class Audio:
    """Store the microphone selected for one application run."""

    def __init__(self, audio_info: AudioInfo) -> None:
        """Save the selected microphone information for this program run."""
        # Nothing is written to a file, so the user chooses again after the
        # program exits and starts a new run.
        self.info = audio_info

    @staticmethod
    def list_devices() -> list[AudioInfo]:
        """Return every device that can record audio."""
        microphones: list[AudioInfo] = []

        # query_devices() includes both input devices (microphones) and output
        # devices (speakers). enumerate() preserves sounddevice's device index.
        for index, device in enumerate(sd.query_devices()):
            input_channels = int(device["max_input_channels"])

            # A device with zero input channels cannot record audio.
            if input_channels == 0:
                continue

            microphones.append(
                AudioInfo(
                    index=index,
                    name=str(device["name"]),
                    channels=input_channels,
                    samplerate=float(device["default_samplerate"]),
                )
            )

        return microphones
