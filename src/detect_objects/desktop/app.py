"""Application entry point for the isolated PySide desktop pipeline."""

from __future__ import annotations

from collections.abc import Sequence
import sys

from PySide6.QtWidgets import QApplication

from ..device_setup.context import Context
from .runtime_window import RuntimeWindow


def run_desktop_app(
    context: Context | None = None,
    arguments: Sequence[str] | None = None,
) -> int:
    """Open the standalone desktop shell and run its Qt event loop."""
    application = QApplication(
        list(sys.argv if arguments is None else arguments),
    )
    window = RuntimeWindow(context=context)
    window.show()
    return application.exec()
