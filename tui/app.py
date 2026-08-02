"""Top-level Textual application for ODIA."""

from __future__ import annotations

from textual.app import App

from device_setup import Context
from tui.device_setup_screen import DeviceSetupScreen


class OdiaApp(App[Context | None]):
    """Own the Textual shell and application screen flow."""

    TITLE = "ODIA"
    SUB_TITLE = "Object detection and voice control"

    CSS = """
    Screen {
        align: center middle;
    }

    #setup-panel {
        width: 64;
        height: auto;
        padding: 1 2;
        border: round $accent;
        background: $panel;
    }

    .field-label {
        margin-top: 1;
    }

    Select {
        width: 100%;
        margin-bottom: 1;
    }

    #continue {
        width: 100%;
        margin-top: 1;
    }

    #status {
        height: auto;
        margin-top: 1;
        text-align: center;
    }
    """

    BINDINGS = [("q", "quit", "Quit")]

    def on_mount(self) -> None:
        """Open device setup as the first application screen."""
        self.push_screen(DeviceSetupScreen(), self.finish_device_setup)

    def finish_device_setup(self, context: Context | None) -> None:
        """Return the context until the runtime dashboard is implemented."""
        self.exit(context)


def run_app() -> Context | None:
    """Run the Textual shell and return its selected runtime context."""
    return OdiaApp().run()


def main() -> int:
    """Run the current Textual application."""
    context = run_app()
    if context is None:
        return 1

    print(f"Camera: {context.camera.info.name}")
    print(f"Microphone: {context.audio.info.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
