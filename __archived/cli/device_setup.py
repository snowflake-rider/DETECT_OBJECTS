"""Rich command-line interface for selecting and testing devices."""

from __future__ import annotations

import math
import time

import cv2
import sounddevice as sd
from rich.console import Console
from rich.live import Live
from rich.prompt import Confirm, IntPrompt
from rich.table import Table
from rich.text import Text

from device_setup import (
    AudioInput,
    AudioInputInfo,
    AudioOutput,
    AudioOutputInfo,
    Camera,
    CameraInfo,
    Context,
    Environment,
)

SILENCE_DB = -60.0
console = Console()


def choose_camera() -> CameraInfo | None:
    """Display available cameras and return the selected device information."""
    cameras = Camera.list_devices()
    if not cameras:
        console.print("[yellow]No available cameras were found.[/yellow]")
        return None

    table = Table(title="Available Cameras")
    table.add_column("Choice", justify="right", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Backend")

    for choice, camera in enumerate(cameras, start=1):
        backend_name = cv2.videoio_registry.getBackendName(camera.backend)
        table.add_row(str(choice), camera.name, backend_name)

    console.print(table)
    while True:
        choice = IntPrompt.ask(
            f"Choose a camera [1-{len(cameras)}], or 0 to cancel",
            default=0,
        )
        if choice == 0:
            return None
        if 1 <= choice <= len(cameras):
            return cameras[choice - 1]
        console.print(f"[red]Enter a number between 1 and {len(cameras)}.[/red]")


def test_camera(camera: Camera) -> bool:
    """Open an OpenCV preview for the selected camera."""
    capture = cv2.VideoCapture(camera.info.index, camera.info.backend)
    try:
        if not capture.isOpened():
            console.print(f"[red]Could not open '{camera.info.name}'.[/red]")
            return False

        console.print("[green]Camera opened. Press Q or Escape to close.[/green]")
        while True:
            success, frame = capture.read()
            if not success or frame is None:
                console.print("[red]Could not read a frame.[/red]")
                return False

            cv2.imshow(camera.info.name, frame)
            if cv2.waitKey(1) & 0xFF in (ord("q"), 27):
                return True
    finally:
        capture.release()
        cv2.destroyAllWindows()


def setup_camera() -> Camera | None:
    """Select a camera and optionally preview it."""
    selected_info = choose_camera()
    if selected_info is None:
        console.print("[yellow]No camera selected.[/yellow]")
        return None

    camera = Camera(selected_info)
    console.print(f"[green]Selected '{camera.info.name}'.[/green]")
    if not Confirm.ask(
        f"Do you want to test '{selected_info.name}'?",
        default=False,
    ):
        console.print("[yellow]Skipping camera test.[/yellow]")
        return camera

    if not test_camera(camera):
        console.print("[red]Camera test failed.[/red]")
        return None
    console.print("[green]Camera test completed.[/green]")
    return camera


def choose_audio_input() -> AudioInputInfo | None:
    """Display available microphones and return the selected device information."""
    microphones = AudioInput.list_devices()
    if not microphones:
        console.print("[yellow]No input audio devices were found.[/yellow]")
        return None

    default_input_index = int(sd.default.device[0])
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

    console.print(table)
    while True:
        choice = IntPrompt.ask(
            f"Choose a microphone [1-{len(microphones)}], or 0 to cancel",
            default=0,
        )
        if choice == 0:
            return None
        if 1 <= choice <= len(microphones):
            return microphones[choice - 1]
        console.print(f"[red]Enter a number between 1 and {len(microphones)}.[/red]")


def level_bar(rms: float, width: int = 30) -> Text:
    """Convert an RMS audio level into a Rich decibel bar."""
    decibels = 20 * math.log10(max(rms, 1e-10))
    ratio = min(max((decibels - SILENCE_DB) / -SILENCE_DB, 0.0), 1.0)
    filled = int(ratio * width)
    bar = "█" * filled + "░" * (width - filled)
    return Text(f"Sound Level [{bar}] {decibels:6.1f} dB")


def test_audio_input(audio_input: AudioInput) -> bool:
    """Display live microphone input level until the user presses Ctrl+C."""
    rms = 0.0
    received_audio = False

    def record(indata, frames, time_info, status) -> None:
        nonlocal rms, received_audio
        rms = math.sqrt(float((indata**2).mean()))
        received_audio = True

    console.print(
        f"[green]Testing '{audio_input.info.name}'. Speak into the microphone.[/green]"
    )
    console.print("[cyan]Press Ctrl+C when you are ready to stop the test.[/cyan]")

    try:
        with sd.InputStream(
            device=audio_input.info.index,
            channels=1,
            samplerate=audio_input.info.samplerate,
            callback=record,
        ):
            with Live(console=console, refresh_per_second=20) as live:
                while True:
                    live.update(level_bar(rms))
                    time.sleep(0.05)
    except KeyboardInterrupt:
        console.print()
        console.print("[yellow]Sound-level test stopped.[/yellow]")
    except sd.PortAudioError as error:
        console.print(f"[red]Could not test the microphone: {error}[/red]")
        return False

    if received_audio:
        console.print("[green]Microphone test completed.[/green]")
    else:
        console.print("[red]No audio samples were received.[/red]")
    return received_audio


def setup_audio_input() -> AudioInput | None:
    """Select a microphone and optionally test its input level."""
    selected_info = choose_audio_input()
    if selected_info is None:
        console.print("[yellow]No microphone selected.[/yellow]")
        return None

    audio_input = AudioInput(selected_info)
    console.print(f"[green]Selected '{audio_input.info.name}'.[/green]")
    if not Confirm.ask(
        f"Do you want to test '{selected_info.name}'?",
        default=False,
    ):
        console.print("[yellow]Skipping audio test.[/yellow]")
        return audio_input

    if not test_audio_input(audio_input):
        console.print("[red]Microphone test failed.[/red]")
        return None
    console.print("[green]Microphone test completed.[/green]")
    return audio_input


def choose_audio_output() -> AudioOutputInfo | None:
    """Display audio outputs and return the selected device information."""
    outputs = AudioOutput.list_devices()
    if not outputs:
        console.print("[yellow]No audio output devices were found.[/yellow]")
        return None

    default_output_index = int(sd.default.device[1])
    table = Table(title="Available Audio Outputs")
    table.add_column("Choice", justify="right", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Sample Rate", justify="right")
    table.add_column("Default", justify="center")

    for choice, output in enumerate(outputs, start=1):
        table.add_row(
            str(choice),
            output.name,
            f"{output.samplerate:.0f} Hz",
            "✅" if output.index == default_output_index else "",
        )

    console.print(table)
    while True:
        choice = IntPrompt.ask(
            f"Choose an audio output [1-{len(outputs)}], or 0 to cancel",
            default=0,
        )
        if choice == 0:
            return None
        if 1 <= choice <= len(outputs):
            return outputs[choice - 1]
        console.print(f"[red]Enter a number between 1 and {len(outputs)}.[/red]")


def setup_audio_output() -> AudioOutput | None:
    """Select the audio output used for application playback."""
    selected_info = choose_audio_output()
    if selected_info is None:
        console.print("[yellow]No audio output selected.[/yellow]")
        return None

    audio_output = AudioOutput(selected_info)
    console.print(f"[green]Selected '{audio_output.info.name}'.[/green]")
    return audio_output


def build_context() -> Context | None:
    """Collect both device choices and build one runtime context."""
    camera = setup_camera()
    audio_input = setup_audio_input()
    audio_output = setup_audio_output()
    if camera is None or audio_input is None or audio_output is None:
        console.print("[red]Context setup is incomplete.[/red]")
        return None
    return Context(
        environment=Environment.detect(),
        camera=camera,
        audio_input=audio_input,
        audio_output=audio_output,
    )


def show_summary(context: Context) -> None:
    """Display the environment and selected input devices."""
    table = Table(title="Context")
    table.add_column("Type", style="cyan")
    table.add_column("Name", style="green")
    table.add_row(
        "Environment",
        f"{context.environment.os} ({context.environment.machine})",
    )
    table.add_row("Camera", context.camera.info.name)
    table.add_row("Audio Input", context.audio_input.info.name)
    table.add_row("Audio Output", context.audio_output.info.name)
    console.print(table)


def main() -> int:
    """Run the Rich device setup interface."""
    context = build_context()
    if context is None:
        return 1
    show_summary(context)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
