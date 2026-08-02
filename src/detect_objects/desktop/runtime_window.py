"""PySide window for the isolated ODIA desktop runtime."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class RuntimeWindow(QMainWindow):
    """Present the first hardware-free desktop dashboard shell."""

    command_submitted = Signal(str)
    stop_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ODIA Desktop")
        self.resize(1100, 700)
        self.setMinimumSize(800, 520)
        self.setCentralWidget(self._build_content())
        self.setStyleSheet(self._stylesheet())

    def _build_content(self) -> QWidget:
        content = QWidget()
        page = QVBoxLayout(content)
        page.setContentsMargins(24, 20, 24, 20)
        page.setSpacing(16)

        brand = QLabel("ODIA  ·  DESKTOP RUNTIME")
        brand.setObjectName("brand")
        page.addWidget(brand)

        columns = QHBoxLayout()
        columns.setSpacing(18)
        columns.addWidget(self._build_video_panel(), stretch=3)
        columns.addWidget(self._build_runtime_panel(), stretch=2)
        page.addLayout(columns, stretch=1)

        return content

    def _build_video_panel(self) -> QLabel:
        video_panel = QLabel("Camera preview will appear here")
        video_panel.setObjectName("video-panel")
        video_panel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        video_panel.setMinimumSize(480, 360)
        return video_panel

    def _build_runtime_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("runtime-panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        heading = QLabel("Runtime status")
        heading.setObjectName("panel-heading")
        layout.addWidget(heading)

        yolo_status = QLabel("YOLO: Not started")
        yolo_status.setObjectName("yolo-status")
        layout.addWidget(yolo_status)

        whisper_status = QLabel("Whisper: Not started")
        whisper_status.setObjectName("whisper-status")
        layout.addWidget(whisper_status)

        transcript_heading = QLabel("Latest transcript")
        transcript_heading.setObjectName("section-heading")
        layout.addWidget(transcript_heading)

        transcript = QLabel("No transcript yet")
        transcript.setObjectName("transcript")
        transcript.setWordWrap(True)
        transcript.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(transcript, stretch=1)

        command_input = QLineEdit()
        command_input.setObjectName("command-input")
        command_input.setPlaceholderText("Type an object command…")
        command_input.returnPressed.connect(self._submit_command)
        layout.addWidget(command_input)

        actions = QHBoxLayout()
        send_button = QPushButton("Send command")
        send_button.setObjectName("send-command")
        send_button.clicked.connect(self._submit_command)
        actions.addWidget(send_button)

        stop_button = QPushButton("Stop")
        stop_button.setObjectName("stop-runtime")
        stop_button.clicked.connect(self._request_stop)
        actions.addWidget(stop_button)
        layout.addLayout(actions)

        return panel

    def _submit_command(self) -> None:
        command_input = self.findChild(QLineEdit, "command-input")
        command = command_input.text().strip()
        if not command:
            return

        self.findChild(QLabel, "transcript").setText(f"Typed command: {command}")
        command_input.clear()
        self.command_submitted.emit(command)

    def _request_stop(self) -> None:
        self.stop_requested.emit()
        self.close()

    @staticmethod
    def _stylesheet() -> str:
        return """
        QMainWindow, QWidget {
            background: #111318;
            color: #e7eaf0;
            font-size: 14px;
        }
        QLabel#brand {
            color: #ffb454;
            font-size: 20px;
            font-weight: 700;
        }
        QLabel#video-panel {
            background: #080a0e;
            border: 2px solid #353b48;
            border-radius: 10px;
            color: #8d95a5;
            font-size: 17px;
        }
        QFrame#runtime-panel {
            background: #1a1e25;
            border: 1px solid #353b48;
            border-radius: 10px;
        }
        QLabel#panel-heading {
            color: #ffb454;
            font-size: 18px;
            font-weight: 700;
        }
        QLabel#section-heading {
            color: #9aa3b4;
            font-weight: 600;
            margin-top: 10px;
        }
        QLabel#transcript {
            background: #12151a;
            border-radius: 6px;
            color: #c9cfda;
            padding: 12px;
        }
        QLineEdit {
            background: #0f1217;
            border: 1px solid #4a5261;
            border-radius: 6px;
            padding: 10px;
        }
        QLineEdit:focus {
            border-color: #ffb454;
        }
        QPushButton {
            background: #2b313c;
            border: 1px solid #4a5261;
            border-radius: 6px;
            padding: 10px 14px;
        }
        QPushButton:hover {
            background: #394150;
        }
        QPushButton#send-command {
            background: #c97a22;
            border-color: #e99b43;
            font-weight: 600;
        }
        """
