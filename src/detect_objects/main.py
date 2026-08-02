"""Start device setup, prepare the models, and run ODIA."""

from .launch_mode import RuntimeMode
from .runtime import LocalRuntime
from .tui.app import run_app, run_startup_app


def _run_desktop_mode() -> int:
    """Import and run optional PySide code only after Desktop is selected."""
    from .desktop.app import run_desktop_app

    return run_desktop_app()


def main() -> int:
    """Run the setup screens followed by voice and camera detection."""
    context = run_app()
    if context is None:
        return 1

    if context.runtime_mode is RuntimeMode.DESKTOP:
        return _run_desktop_mode()

    runtime = LocalRuntime(context)
    try:
        if not run_startup_app(runtime.prepare, context.ui_theme):
            return 1
        runtime.run()
    except KeyboardInterrupt:
        print("종료 요청을 받았습니다.")
    finally:
        runtime.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
