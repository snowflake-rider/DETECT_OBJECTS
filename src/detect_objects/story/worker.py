"""Run story generation without blocking the PySide event loop."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal

from .generator import StoryGenerator


class StoryWorker(QThread):
    """Generate one session story on a background Qt thread."""

    completed = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        generator: StoryGenerator,
        session_dir: Path,
        *,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._generator = generator
        self._session_dir = session_dir

    def run(self) -> None:
        try:
            result = self._generator.generate(self._session_dir)
        except Exception as error:
            self.failed.emit(str(error))
            return
        self.completed.emit(result)
