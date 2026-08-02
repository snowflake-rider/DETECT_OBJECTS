"""Discover and store selected audio input and output devices."""

from __future__ import annotations

from dataclasses import dataclass

import sounddevice as sd


@dataclass(frozen=True)
class AudioInputInfo:
    """Information needed to identify and open one audio input device."""

    # This index is the value sounddevice expects when opening an input stream.
    index: int
    name: str
    channels: int
    samplerate: float


class AudioInput:
    """Store the audio input selected for one application run."""

    def __init__(self, info: AudioInputInfo) -> None:
        """Save the selected audio input information for this program run."""
        # Nothing is written to a file, so the user chooses again after the
        # program exits and starts a new run.
        self.info = info

    @staticmethod
    def list_devices() -> list[AudioInputInfo]:
        """Return every device that can record audio."""
        inputs: list[AudioInputInfo] = []

        # query_devices() includes both input devices (microphones) and output
        # devices (speakers). enumerate() preserves sounddevice's device index.
        for index, device in enumerate(sd.query_devices()):
            input_channels = int(device["max_input_channels"])

            # A device with zero input channels cannot record audio.
            if input_channels == 0:
                continue

            inputs.append(
                AudioInputInfo(
                    index=index,
                    name=str(device["name"]),
                    channels=input_channels,
                    samplerate=float(device["default_samplerate"]),
                )
            )

        return inputs


@dataclass(frozen=True)
class AudioOutputInfo:
    """Information needed to identify and open one audio output device."""

    index: int
    name: str
    channels: int
    samplerate: float


class AudioOutput:
    """Store the audio output selected for one application run."""

    def __init__(self, info: AudioOutputInfo) -> None:
        """Save the selected audio output information for this program run."""
        self.info = info

    @staticmethod
    def list_devices() -> list[AudioOutputInfo]:
        """Return every device that can play audio."""
        outputs: list[AudioOutputInfo] = []

        for index, device in enumerate(sd.query_devices()):
            output_channels = int(device["max_output_channels"])
            if output_channels == 0:
                continue

            outputs.append(
                AudioOutputInfo(
                    index=index,
                    name=str(device["name"]),
                    channels=output_channels,
                    samplerate=float(device["default_samplerate"]),
                )
            )

        return outputs
