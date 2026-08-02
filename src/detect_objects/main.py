"""Start device setup, prepare the models, and run ODIA."""

# Context stores the choices made on the setup screens.
from .device_setup.context import Context

# RuntimeMode tells us whether the user chose Classic or Desktop mode.
from .launch_mode import RuntimeMode

# LocalRuntime manages the camera, microphone, models, threads, and cleanup.
from .runtime import LocalRuntime

# run_app() shows the setup screens and collects the user's choices.
# run_startup_app() shows a screen while the models are being prepared.
from .tui.app import run_app, run_startup_app


def _run_desktop_mode(context: Context) -> int:
    """Import and run optional PySide code only after Desktop is selected."""
    # This import happens here, not at the top of the file.
    # Therefore, PySide is loaded only when Desktop mode is selected.
    from .desktop.app import run_desktop_app

    # Give the user's setup choices to the Desktop application.
    # Return its exit code to the terminal.
    return run_desktop_app(context=context)


def main() -> int:
    """Run the setup screens followed by voice and camera detection."""
    # The program starts by showing the setup TUI.
    # It waits here until the user finishes or closes the setup.
    context = run_app()

    # context contains the user's choices, such as:
    # camera, microphone, models, theme, and runtime mode.
    # run_app() returns None if the user closes the setup early.
    if context is None:
        # Stop here. Exit code 1 means the application did not start normally.
        return 1

    # If the user selected Desktop, run the Desktop application and stop here.
    if context.runtime_mode is RuntimeMode.DESKTOP:
        return _run_desktop_mode(context)

    # Otherwise, continue below with Classic mode.
    # This creates the runtime manager, but it does not load the models yet.
    runtime = LocalRuntime(context)

    # try watches the startup and running code for problems or Ctrl+C.
    try:
        # runtime.prepare has no (). We pass the function itself to the TUI.
        # The startup TUI calls it in a worker thread and shows its progress.
        # prepare() validates classes and prepares the models and devices.
        # The result is True only when preparation succeeds and the user continues.
        if not run_startup_app(runtime.prepare, context.ui_theme):
            # Stop if preparation failed or the startup screen was closed.
            return 1

        # Everything is prepared, so start voice and camera processing.
        runtime.run()

    # Ctrl+C raises KeyboardInterrupt and brings the program here.
    except KeyboardInterrupt:
        print("종료 요청을 받았습니다.")

    # finally always runs: success, error, Ctrl+C, or an early return.
    finally:
        # Stop threads and release the camera, microphone, and models.
        runtime.close()

    # Reaching here means the application ended normally.
    # __main__.py gives this 0 exit code to the terminal.
    return 0


# Importing this file defines main(), but does not call it.
# During an import, __name__ is "detect_objects.main", not "__main__".
# Therefore, this condition is false during an import.
# It is true when running: python -m detect_objects.main
if __name__ == "__main__":
    # Run the application, then send its exit code to the terminal.
    raise SystemExit(main())
