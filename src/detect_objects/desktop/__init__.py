"""Standalone PySide desktop pipeline for ODIA."""

from .app import run_desktop_app
from .runtime_window import RuntimeWindow

__all__ = ["RuntimeWindow", "run_desktop_app"]
