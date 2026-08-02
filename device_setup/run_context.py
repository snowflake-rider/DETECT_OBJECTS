"""Build and display the context for one interactive application run."""

from __future__ import annotations

from rich.console import Console
from rich.table import Table

from .audio import Audio
from .camera import Camera
from .context import Context
from .environment import Environment


console = Console()


def build_context() -> Context | None:
    """Detect the environment and collect both interactive device choices."""
    environment = Environment.detect()

    # Each device module owns its selection and optional test workflow.
    camera = Camera.setup()
    audio = Audio.setup()

    # Context represents a complete run, so do not create a partial one.
    if camera is None or audio is None:
        console.print("[red]Context setup is incomplete.[/red]")
        return None

    return Context(
        environment=environment,
        camera=camera,
        audio=audio,
    )


def show_summary(context: Context) -> None:
    """Display the environment and input devices stored in the context."""
    table = Table(title="Context")
    table.add_column("Type", style="cyan")
    table.add_column("Name", style="green")

    table.add_row(
        "Environment",
        f"{context.environment.os} ({context.environment.machine})",
    )
    table.add_row(
        "Camera",
        context.camera.info.name,
    )
    table.add_row(
        "Audio",
        context.audio.info.name,
    )

    console.print(table)


def main() -> int:
    """Build and display the context for this application run."""
    context = build_context()

    if context is None:
        return 1

    show_summary(context)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
