"""Start device setup, prepare the models, and run ODIA."""

from .runtime import LocalRuntime
from .tui.app import run_app, run_startup_app


def main() -> int:
    """Run the setup screens followed by voice and camera detection."""
    context = run_app()
    if context is None:
        return 1

    runtime = LocalRuntime(context)
    try:
        if not run_startup_app(runtime.prepare):
            return 1
        runtime.run()
    except KeyboardInterrupt:
        print("종료 요청을 받았습니다.")
    finally:
        runtime.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
