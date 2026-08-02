"""Run the isolated ODIA desktop shell with ``python -m detect_objects.desktop``."""

from .app import run_desktop_app

if __name__ == "__main__":
    raise SystemExit(run_desktop_app())
