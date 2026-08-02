"""Run the selected microphone and Whisper model away from the Qt UI thread."""

from __future__ import annotations

from threading import Event
from typing import Protocol

from PySide6.QtCore import QObject, QThread, Signal

from ..models.factory import create_voice_manager


class VoiceManager(Protocol):
    """Whisper operations needed by the desktop worker."""

    def load_model(self) -> None: ...

    def create_stream(self) -> None: ...

    def start(self) -> None: ...

    def get_transcribed_text(self, timeout: float | None = None) -> str | None: ...

    def close(self) -> None: ...


class VoiceManagerFactory(Protocol):
    """Construct the selected voice manager for one microphone."""

    def __call__(self, model_id: str, *, device_id: int) -> VoiceManager: ...


class WhisperStream(QThread):
    """Emit transcripts from a user-controlled Whisper worker."""

    status_changed = Signal(str)
    transcript_ready = Signal(str)
    error = Signal(str)

    def __init__(
        self,
        *,
        model_id: str,
        device_id: int,
        manager_factory: VoiceManagerFactory = create_voice_manager,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._model_id = model_id
        self._device_id = device_id
        self._manager_factory = manager_factory
        self._stop_requested = Event()

    @property
    def is_running(self) -> bool:
        """Return whether Whisper is loading, listening, or stopping."""
        return self.isRunning()

    def start(self) -> None:
        """Start Whisper unless its worker is already active."""
        if self.is_running:
            return
        self._stop_requested.clear()
        super().start()

    def stop(self) -> None:
        """Ask Whisper to stop after its current model operation."""
        self._stop_requested.set()
        if self.is_running:
            self.status_changed.emit("Stopping…")

    def run(self) -> None:
        """Own the microphone and selected Whisper model until stopped."""
        manager: VoiceManager | None = None
        failed = False
        try:
            self.status_changed.emit("Loading model…")
            manager = self._manager_factory(
                self._model_id,
                device_id=self._device_id,
            )
            manager.load_model()
            if self._stop_requested.is_set():
                return

            self.status_changed.emit("Connecting microphone…")
            manager.create_stream()
            manager.start()
            self.status_changed.emit("Listening")

            while not self._stop_requested.is_set():
                transcript = manager.get_transcribed_text(timeout=0.25)
                if transcript:
                    self.transcript_ready.emit(transcript)
        except (OSError, RuntimeError, TypeError, ValueError) as error:
            failed = True
            self.error.emit(f"Whisper failed: {error}")
        finally:
            if manager is not None:
                try:
                    manager.close()
                except (OSError, RuntimeError) as error:
                    failed = True
                    self.error.emit(f"Whisper cleanup failed: {error}")
            self.status_changed.emit("Error" if failed else "Off")
