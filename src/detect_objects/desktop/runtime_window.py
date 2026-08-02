"""PySide window for the isolated ODIA desktop runtime."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtGui import QCloseEvent, QImage, QPixmap, QResizeEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..device_setup.context import Context
from ..models.catalog import get_model_option
from ..voice_text_convert.parse_and_match_module import Text_Manager
from .camera_video import CameraVideoStream
from .fake_video import FakeVideoStream
from .whisper_stream import WhisperStream
from .yolo_detection import YoloDetector

VideoStream = FakeVideoStream | CameraVideoStream


class RuntimeWindow(QMainWindow):
    """Present live vision, voice control, and typed object instructions."""

    command_submitted = Signal(str)
    quit_requested = Signal()

    def __init__(
        self,
        context: Context | None = None,
        video_stream: VideoStream | None = None,
    ) -> None:
        super().__init__()
        self._context = context
        self._current_frame: QImage | None = None
        self._text_manager_context = Text_Manager()
        self._text_manager = self._text_manager_context.__enter__()
        supported_classes = self._text_manager.get_supported_yolo_classes()
        if video_stream is not None:
            self._video_stream = video_stream
        elif context is not None:
            camera = context.camera.info
            self._video_stream = CameraVideoStream(
                index=camera.index,
                backend=camera.backend,
                name=camera.name,
                detector=YoloDetector(
                    context.models.vision_id,
                    supported_classes=supported_classes,
                ),
                parent=self,
            )
        else:
            self._video_stream = FakeVideoStream(parent=self)
        self._whisper_stream = (
            WhisperStream(
                model_id=context.models.voice_id,
                device_id=context.audio_input.info.index,
                parent=self,
            )
            if context is not None
            else None
        )
        self.setWindowTitle("ODIA Live")
        self.resize(1280, 800)
        self.setMinimumSize(900, 620)
        self.setCentralWidget(self._build_content())
        self.setStyleSheet(self._stylesheet())
        self._video_stream.frame_ready.connect(self.display_frame)
        self._video_stream.error.connect(self.show_video_error)
        self._video_stream.model_status.connect(self.show_model_status)
        self._video_stream.detections_ready.connect(self.show_detections)
        if self._whisper_stream is not None:
            self._whisper_stream.status_changed.connect(self.show_whisper_status)
            self._whisper_stream.transcript_ready.connect(self.receive_transcript)
            self._whisper_stream.error.connect(self.show_whisper_error)
            self._whisper_stream.finished.connect(self._whisper_finished)
        self._video_stream.start()
        QTimer.singleShot(0, self._refresh_video_panel)

    @property
    def video_stream(self) -> VideoStream:
        """Return the preview source so its lifecycle can be inspected."""
        return self._video_stream

    def _build_content(self) -> QWidget:
        content = QWidget()
        page = QVBoxLayout(content)
        page.setContentsMargins(16, 14, 16, 14)
        page.setSpacing(12)
        page.addWidget(self._build_top_rail())
        page.addWidget(self._build_video_panel(), stretch=1)
        page.addWidget(self._build_command_dock())

        return content

    def _build_top_rail(self) -> QFrame:
        rail = QFrame()
        rail.setObjectName("top-rail")
        layout = QVBoxLayout(rail)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        primary_row = QHBoxLayout()
        primary_row.setSpacing(12)

        brand = QLabel("ODIA")
        brand.setObjectName("brand")
        primary_row.addWidget(brand)

        live_status = QLabel("● LIVE")
        live_status.setObjectName("live-status")
        primary_row.addWidget(live_status)
        primary_row.addStretch()

        preview_button = QPushButton("Pause")
        preview_button.setObjectName("toggle-preview")
        preview_button.clicked.connect(self._toggle_preview)
        primary_row.addWidget(preview_button)

        quit_button = QPushButton("Quit")
        quit_button.setObjectName("quit-runtime")
        quit_button.clicked.connect(self._request_quit)
        primary_row.addWidget(quit_button)
        layout.addLayout(primary_row)

        if self._context is not None:
            camera = self._context.camera.info
            camera_name = f"{camera.name} · index {camera.index}"
            yolo_name = get_model_option(
                self._context.models.vision_id,
                kind="vision",
            ).name
            whisper_name = get_model_option(
                self._context.models.voice_id,
                kind="voice",
            ).name
            yolo_status = "Not started"
        else:
            camera_name = "Synthetic preview"
            yolo_name = "Simulation"
            whisper_name = "No setup context"
            yolo_status = "Simulation ready"

        dashboard = QHBoxLayout()
        dashboard.setSpacing(10)
        dashboard.addWidget(
            self._build_status_card(
                title="CAMERA",
                value=camera_name,
                value_name="camera-selection",
                status="Opening selected device…",
                status_name="camera-runtime-status",
            ),
            stretch=1,
        )
        dashboard.addWidget(
            self._build_status_card(
                title="YOLO VISION",
                value=yolo_name,
                value_name="yolo-model",
                status=yolo_status,
                status_name="yolo-status",
            ),
            stretch=1,
        )
        dashboard.addWidget(self._build_whisper_card(whisper_name), stretch=1)
        layout.addLayout(dashboard)

        if self._context is not None:
            devices = QLabel(
                f"MIC  {self._context.audio_input.info.name}"
                f"     •     OUTPUT  {self._context.audio_output.info.name}"
            )
        else:
            devices = QLabel("MIC  Not connected     •     OUTPUT  Not connected")
        devices.setObjectName("audio-device-summary")
        devices.setToolTip(devices.text())
        layout.addWidget(devices)

        return rail

    @staticmethod
    def _build_status_card(
        *,
        title: str,
        value: str,
        value_name: str,
        status: str,
        status_name: str,
    ) -> QFrame:
        card = QFrame()
        card.setObjectName("status-card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        heading = QLabel(title)
        heading.setObjectName("status-heading")
        layout.addWidget(heading)

        value_label = QLabel(value)
        value_label.setObjectName(value_name)
        value_label.setToolTip(value)
        layout.addWidget(value_label)

        status_label = QLabel(status)
        status_label.setObjectName(status_name)
        layout.addWidget(status_label)
        return card

    def _build_whisper_card(self, model_name: str) -> QFrame:
        card = QFrame()
        card.setObjectName("status-card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 8, 10, 8)
        layout.setSpacing(3)

        heading_row = QHBoxLayout()
        heading = QLabel("WHISPER VOICE")
        heading.setObjectName("status-heading")
        heading_row.addWidget(heading)
        heading_row.addStretch()

        toggle = QPushButton("Start listening")
        toggle.setObjectName("toggle-whisper")
        toggle.clicked.connect(self._toggle_whisper)
        toggle.setEnabled(self._whisper_stream is not None)
        heading_row.addWidget(toggle)
        layout.addLayout(heading_row)

        model = QLabel(model_name)
        model.setObjectName("whisper-model")
        model.setToolTip(model_name)
        layout.addWidget(model)

        status = QLabel("Off" if self._whisper_stream is not None else "Unavailable")
        status.setObjectName("whisper-status")
        layout.addWidget(status)
        return card

    def _build_video_panel(self) -> QLabel:
        video_panel = QLabel("Camera preview will appear here")
        video_panel.setObjectName("video-panel")
        video_panel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        video_panel.setMinimumSize(640, 360)
        video_panel.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        return video_panel

    def _build_command_dock(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("command-dock")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(9)

        detection_row = QHBoxLayout()
        detection_heading = QLabel("DETECTIONS")
        detection_heading.setObjectName("rail-label")
        detection_row.addWidget(detection_heading)
        detection_count = QLabel("0 objects")
        detection_count.setObjectName("detection-count")
        detection_row.addWidget(detection_count)

        detection_summary = QLabel("No objects")
        detection_summary.setObjectName("detection-summary")
        detection_row.addWidget(detection_summary, stretch=1)
        layout.addLayout(detection_row)

        target_row = QHBoxLayout()
        target_heading = QLabel("TARGETS")
        target_heading.setObjectName("rail-label")
        target_row.addWidget(target_heading)
        targets = QLabel("cell phone · clock · keyboard · person")
        targets.setObjectName("target-summary")
        targets.setWordWrap(True)
        target_row.addWidget(targets, stretch=1)
        layout.addLayout(target_row)

        transcript_row = QHBoxLayout()
        transcript_heading = QLabel("INSTRUCTION")
        transcript_heading.setObjectName("rail-label")
        transcript_row.addWidget(transcript_heading)
        transcript = QLabel("Speak with Whisper or type below")
        transcript.setObjectName("transcript")
        transcript.setWordWrap(True)
        transcript_row.addWidget(transcript, stretch=1)
        layout.addLayout(transcript_row)

        command_row = QHBoxLayout()
        command_input = QLineEdit()
        command_input.setObjectName("command-input")
        command_input.setPlaceholderText(
            "Type an object instruction, for example: 사람을 찾아줘"
        )
        command_input.returnPressed.connect(self._submit_command)
        command_row.addWidget(command_input, stretch=1)

        send_button = QPushButton("Send")
        send_button.setObjectName("send-command")
        send_button.clicked.connect(self._submit_command)
        command_row.addWidget(send_button)
        layout.addLayout(command_row)

        return panel

    def _submit_command(self) -> None:
        command_input = self.findChild(QLineEdit, "command-input")
        command = command_input.text().strip()
        if not command:
            return

        self._apply_instruction(command, source="Typed")
        command_input.clear()
        self.command_submitted.emit(command)

    def _apply_instruction(self, text: str, *, source: str) -> None:
        """Parse typed or spoken text and switch YOLO to matching classes."""
        self.findChild(QLabel, "transcript").setText(f"{source}: {text}")
        try:
            detected_classes = self._text_manager.extract(text)
        except (RuntimeError, ValueError) as error:
            self.findChild(QLabel, "target-summary").setText(
                f"Could not parse instruction: {error}"
            )
            return

        classes = tuple(
            dict.fromkeys(detected.yolo_class for detected in detected_classes)
        )
        if not classes:
            self.findChild(QLabel, "target-summary").setText(
                "No supported object found; current targets unchanged"
            )
            return

        self._video_stream.set_classes(classes)
        self.findChild(QLabel, "target-summary").setText(" · ".join(classes))

    @Slot(str)
    def receive_transcript(self, transcript: str) -> None:
        """Route recognized speech through the same path as typed input."""
        self._apply_instruction(transcript, source="Heard")

    def _toggle_whisper(self) -> None:
        if self._whisper_stream is None:
            return

        button = self.findChild(QPushButton, "toggle-whisper")
        if self._whisper_stream.is_running:
            button.setEnabled(False)
            self._whisper_stream.stop()
            return

        button.setText("Stop listening")
        self._whisper_stream.start()

    def _toggle_preview(self) -> None:
        preview_button = self.findChild(QPushButton, "toggle-preview")
        if self._video_stream.is_running:
            self._video_stream.stop()
            preview_button.setText("Resume")
            self.findChild(QLabel, "live-status").setText("● PAUSED")
            self.findChild(QLabel, "camera-runtime-status").setText("Paused")
            self.findChild(QLabel, "yolo-status").setText("Stopped")
            return

        self._video_stream.start()
        preview_button.setText("Pause")
        self.findChild(QLabel, "live-status").setText("● LIVE")
        self.findChild(QLabel, "camera-runtime-status").setText("Opening…")

    @Slot(QImage)
    def display_frame(self, image: QImage) -> None:
        """Replace the video panel with the latest available image."""
        self._current_frame = image
        self.findChild(QLabel, "camera-runtime-status").setText("Streaming")
        self._refresh_video_panel()

    @Slot(str)
    def show_video_error(self, message: str) -> None:
        """Keep the dashboard open and explain why previewing stopped."""
        self._video_stream.stop()
        self._current_frame = None

        video_panel = self.findChild(QLabel, "video-panel")
        video_panel.setPixmap(QPixmap())
        video_panel.setText(f"Camera preview unavailable\n{message}")
        self.findChild(QPushButton, "toggle-preview").setText("Resume")
        self.findChild(QLabel, "live-status").setText("● ERROR")
        self.findChild(QLabel, "camera-runtime-status").setText("Error")
        self.findChild(QLabel, "camera-runtime-status").setToolTip(message)
        self.findChild(QLabel, "yolo-status").setText("Stopped")

    @Slot(str)
    def show_model_status(self, status: str) -> None:
        """Present YOLO loading and accelerator status."""
        self.findChild(QLabel, "yolo-status").setText(status)

    @Slot(str)
    def show_whisper_status(self, status: str) -> None:
        """Show whether Whisper is loading, listening, stopping, or off."""
        self.findChild(QLabel, "whisper-status").setText(status)
        button = self.findChild(QPushButton, "toggle-whisper")
        if status == "Listening":
            button.setText("Stop listening")
        elif status in {"Off", "Error"}:
            button.setText("Start listening")
            button.setEnabled(False)

    @Slot(str)
    def show_whisper_error(self, message: str) -> None:
        """Keep the desktop open and retain Whisper failure details."""
        status = self.findChild(QLabel, "whisper-status")
        status.setText("Error")
        status.setToolTip(message)
        self.findChild(QLabel, "transcript").setText(message)

    @Slot()
    def _whisper_finished(self) -> None:
        button = self.findChild(QPushButton, "toggle-whisper")
        button.setText("Start listening")
        button.setEnabled(True)

    @Slot(int, str)
    def show_detections(self, count: int, summary: str) -> None:
        """Present the latest detection count and percentage labels."""
        noun = "object" if count == 1 else "objects"
        self.findChild(QLabel, "detection-count").setText(f"{count} {noun}")
        self.findChild(QLabel, "detection-summary").setText(summary)

    def _refresh_video_panel(self) -> None:
        if self._current_frame is None:
            return

        video_panel = self.findChild(QLabel, "video-panel")
        if video_panel is None:
            return

        pixmap = QPixmap.fromImage(self._current_frame)
        scaled_pixmap = pixmap.scaled(
            video_panel.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        video_panel.setText("")
        video_panel.setPixmap(scaled_pixmap)

    def _request_quit(self) -> None:
        self.quit_requested.emit()
        self.close()

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Rescale the latest frame when the window changes size."""
        super().resizeEvent(event)
        QTimer.singleShot(0, self._refresh_video_panel)

    def closeEvent(self, event: QCloseEvent) -> None:
        """Release camera, Whisper, and parser resources before closing."""
        self._video_stream.stop()
        if self._whisper_stream is not None:
            self._whisper_stream.stop()
            self._whisper_stream.wait()
        self._text_manager_context.__exit__(None, None, None)
        super().closeEvent(event)

    @staticmethod
    def _stylesheet() -> str:
        return """
        QMainWindow, QWidget {
            background: #0b0d10;
            color: #e8ecf2;
            font-size: 14px;
        }
        QFrame#top-rail, QFrame#command-dock {
            background: #111419;
            border: 1px solid #272c34;
            border-radius: 8px;
        }
        QFrame#status-card {
            background: #171b21;
            border: 1px solid #2c323b;
            border-radius: 7px;
        }
        QLabel#brand {
            color: #f2a33a;
            font-size: 22px;
            font-weight: 800;
            letter-spacing: 2px;
        }
        QLabel#live-status {
            color: #49c98b;
            font-size: 13px;
            font-weight: 700;
        }
        QLabel#status-heading {
            color: #8e97a6;
            font-size: 10px;
            font-weight: 800;
            letter-spacing: 1px;
        }
        QLabel#camera-selection,
        QLabel#yolo-model,
        QLabel#whisper-model {
            color: #e8ecf2;
            font-size: 13px;
            font-weight: 700;
        }
        QLabel#camera-runtime-status,
        QLabel#yolo-status,
        QLabel#whisper-status {
            color: #49c98b;
            font-size: 11px;
            font-weight: 700;
        }
        QLabel#audio-device-summary {
            color: #747e8d;
            font-size: 11px;
        }
        QLabel#video-panel {
            background: #050608;
            border: 1px solid #272c34;
            border-radius: 8px;
            color: #8e97a6;
            font-size: 16px;
        }
        QLabel#rail-label {
            color: #8e97a6;
            font-size: 11px;
            font-weight: 700;
            min-width: 82px;
        }
        QLabel#detection-count {
            color: #e8ecf2;
            font-weight: 700;
            min-width: 72px;
        }
        QLabel#detection-summary {
            color: #f2a33a;
            font-weight: 700;
        }
        QLabel#target-summary {
            color: #67c7d4;
            font-weight: 700;
        }
        QLabel#transcript {
            color: #c9cfda;
        }
        QLineEdit {
            background: #090b0e;
            border: 1px solid #343a44;
            border-radius: 6px;
            color: #e8ecf2;
            padding: 9px 11px;
            selection-background-color: #f2a33a;
        }
        QLineEdit:focus {
            border-color: #f2a33a;
        }
        QPushButton {
            background: #20252d;
            border: 1px solid #343a44;
            border-radius: 6px;
            color: #e8ecf2;
            padding: 9px 15px;
            font-weight: 600;
        }
        QPushButton:hover {
            background: #2a3039;
            border-color: #555e6c;
        }
        QPushButton#send-command {
            background: #c77e25;
            border-color: #f2a33a;
            color: #111419;
        }
        QPushButton#toggle-whisper {
            background: #17343a;
            border-color: #2c6973;
            color: #8ee0ea;
            padding: 5px 9px;
            font-size: 11px;
        }
        QPushButton#toggle-whisper:disabled {
            background: #20242a;
            border-color: #30353d;
            color: #68717d;
        }
        QPushButton#quit-runtime {
            background: #d64550;
            border-color: #e86069;
            color: #ffffff;
            font-weight: 800;
        }
        QPushButton#quit-runtime:hover {
            background: #ea5661;
        }
        """
