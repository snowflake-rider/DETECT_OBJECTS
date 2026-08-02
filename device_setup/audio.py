"""Find an input device, let the user choose it, and test its input level."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass

import sounddevice as sd
from rich.console import Console
from rich.live import Live
from rich.prompt import Confirm, IntPrompt
from rich.table import Table
from rich.text import Text


# Values at or below -60 dB are displayed as silence in the level meter.
SILENCE_DB = -60.0


@dataclass(frozen=True)
class AudioInfo:
    """Information needed to identify and open one microphone."""

    # This index is the value sounddevice expects when opening an input stream.
    index: int
    name: str
    channels: int
    samplerate: float


class Audio:
    """Store a selected microphone and provide a live input-level test."""

    # Reuse one Rich console so tables and messages use consistent formatting.
    console = Console()

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

    @classmethod
    def choose(cls) -> AudioInfo | None:
        """Display available microphones and let the user select one."""
        microphones = cls.list_devices()

        if not microphones:
            cls.console.print("[yellow]No input audio devices were found.[/yellow]")
            return None

        # sounddevice stores the default input and output indexes as a pair.
        default_input_index = int(sd.default.device[0])

        # Build a readable terminal table from the microphone information.
        table = Table(title="Available Microphones")
        table.add_column("Choice", justify="right", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Sample Rate", justify="right")
        table.add_column("Default", justify="center")

        for choice, microphone in enumerate(microphones, start=1):
            table.add_row(
                str(choice),
                microphone.name,
                f"{microphone.samplerate:.0f} Hz",
                "✅" if microphone.index == default_input_index else "",
            )

        cls.console.print(table)

        # Keep asking until the user enters a valid menu number or cancels.
        while True:
            choice = IntPrompt.ask(
                f"Choose a microphone [1-{len(microphones)}], or 0 to cancel",
                default=0,
            )

            if choice == 0:
                return None

            if 1 <= choice <= len(microphones):
                # Menu choices start at 1, while list positions start at 0.
                return microphones[choice - 1]

            cls.console.print(
                f"[red]Enter a number between 1 and {len(microphones)}.[/red]"
            )

    @staticmethod
    def _level_bar(rms: float, width: int = 30) -> Text:
        """Convert an RMS audio level into a readable decibel bar."""
        # RMS describes the strength of the audio signal. Convert it to dB so
        # quiet and loud signals fit into a useful -60 dB to 0 dB range.
        decibels = 20 * math.log10(max(rms, 1e-10))
        ratio = min(max((decibels - SILENCE_DB) / -SILENCE_DB, 0.0), 1.0)
        filled = int(ratio * width)
        bar = "█" * filled + "░" * (width - filled)

        return Text(f"Sound Level [{bar}] {decibels:6.1f} dB")

    def test(self) -> bool:
        """Display this microphone's live sound level until Ctrl+C."""
        rms = 0.0
        received_audio = False

        def record(indata, frames, time_info, status) -> None:
            """Receive one audio block from sounddevice's audio thread."""
            # Keep this callback fast: calculate and save only the current
            # level. Rich output happens in the main thread below.
            # nonlocal lets record() update variables from the outer test().
            nonlocal rms, received_audio
            rms = math.sqrt(float((indata**2).mean()))
            received_audio = True

        self.console.print(
            f"[green]Testing '{self.info.name}'. Speak into the microphone.[/green]"
        )
        self.console.print(
            "[cyan]Press Ctrl+C when you are ready to stop the test.[/cyan]"
        )

        try:
            # The context manager closes the microphone stream automatically,
            # including when an exception interrupts the test.
            with sd.InputStream(
                device=self.info.index,
                channels=1,
                samplerate=self.info.samplerate,
                callback=record,
            ):
                # Live redraws one terminal line instead of printing a new line
                # for every audio block. The loop keeps running until Ctrl+C.
                with Live(console=self.console, refresh_per_second=20) as live:
                    while True:
                        live.update(self._level_bar(rms))
                        time.sleep(0.05)
        except KeyboardInterrupt:
            # Ctrl+C stops only this test. Leaving the InputStream context above
            # closes the microphone before the confirmation question appears.
            self.console.print()
            self.console.print("[yellow]Sound-level test stopped.[/yellow]")
        except sd.PortAudioError as error:
            self.console.print(f"[red]Could not test the microphone: {error}[/red]")
            return False

        if received_audio:
            self.console.print("[green]Microphone test completed.[/green]")
        else:
            self.console.print("[red]No audio samples were received.[/red]")

        return received_audio

    @classmethod
    def setup(cls) -> Audio | None:
        """Save the selected microphone and optionally test its Sound Level."""
        selected_info = cls.choose()

        if selected_info is None:
            cls.console.print("[yellow]No microphone selected.[/yellow]")
            return None

        # Record the user's choice immediately. Testing is optional and does not
        # decide whether this Audio object keeps the selected AudioInfo.
        audio = cls(selected_info)
        cls.console.print(f"[green]Selected '{audio.info.name}'.[/green]")

        # Confirm.ask returns True for yes and False for no.
        # default=False means pressing Enter selects no.
        should_test = Confirm.ask(
            f"Do you want to test '{selected_info.name}'?",
            default=False,
        )

        if not should_test:
            cls.console.print("[yellow]Skipping audio test.[/yellow]")
            return audio

        # The Sound Level keeps updating until the user presses Ctrl+C.
        if not audio.test():
            cls.console.print("[red]Microphone test failed.[/red]")
            return None

        cls.console.print("[green]Microphone test completed.[/green]")
        return audio


if __name__ == "__main__":
    # This block runs only when audio.py is executed directly.
    audio = Audio.setup()
